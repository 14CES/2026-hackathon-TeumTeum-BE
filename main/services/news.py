import math
import requests
import unicodedata
from django.conf import settings


def _normalize(text):
    return unicodedata.normalize("NFC", text)


# fallback 검색 결과에서 사용할 관련 키워드 (검색어로도 재사용)
RELATED_KEYWORDS = {
    "스트레스": [
        "스트레스", "불안", "우울", "번아웃",
        "정신건강", "심리", "명상", "마음챙김"
    ],
    "불안": [
        "불안", "스트레스", "우울",
        "정신건강", "심리", "상담"
    ],
    "심리": [
        "심리", "심리학", "심리상담",
        "정신건강", "스트레스",
        "불안", "우울", "상담"
    ],
    "정신건강": [
        "정신건강", "정신질환",
        "심리", "스트레스",
        "불안", "우울", "상담"
    ],
    "수면": [
        "수면", "숙면", "불면", "불면증", "잠"
    ],
    "걷기": [
        "걷기", "산책", "보행",
        "운동", "신체활동"
    ],
    "운동": [
        "운동", "스트레칭", "걷기",
        "근력", "체력", "신체활동"
    ],
    "휴식": [
        "휴식", "쉼", "힐링",
        "재충전", "피로회복", "스트레스"
    ],
    "명상": [
        "명상", "마음챙김", "심리",
        "정신건강", "스트레스"
    ],
    "마음챙김": [
        "마음챙김", "명상", "심리",
        "정신건강", "스트레스"
    ],
    "웰니스": [
        "웰니스", "웰빙", "운동",
        "수면", "휴식", "생활습관"
    ],
    "웰빙": [
        "웰빙", "웰니스", "운동",
        "수면", "휴식"
    ],
    "건강관리": [
        "건강관리", "운동",
        "수면", "식습관", "생활습관"
    ],
    "자기관리": [
        "자기관리", "생활습관",
        "운동", "수면", "식습관"
    ],
    "생활습관": [
        "생활습관", "식습관",
        "운동", "수면"
    ],
    "피로회복": [
        "피로회복", "피로", "휴식",
        "수면"
    ],
    "힐링": [
        "힐링", "휴식", "쉼",
        "여행", "명상"
    ],
    "요가": [
        "요가", "스트레칭", "운동",
        "명상", "호흡"
    ],
    "스트레칭": [
        "스트레칭", "운동", "근육",
        "자세"
    ],
}


def get_news(query, max_results=5):

    url = "https://newsdata.io/api/1/latest"

    # 검색 시도할 검색어 목록 만들기 (최대 5개)
    fallback_queries = [query]

    for keyword, related in RELATED_KEYWORDS.items():
        if keyword in query:
            fallback_queries.extend(related)
            break   # 가장 먼저 매칭되는 카테고리 하나만 사용

    fallback_queries = list(dict.fromkeys(fallback_queries))
    fallback_queries = fallback_queries[:5]

    # 관련성 검사에 사용할 필터 키워드 만들기
    filter_keywords = []

    for keyword, related in RELATED_KEYWORDS.items():
        if keyword in query:
            filter_keywords = list(dict.fromkeys(related))
            break

    if not filter_keywords:
        filter_keywords = query.split()

    print("===== 기사 관련성 필터 =====")
    print("원래 검색어:", query)
    print("검색 시도 순서:", fallback_queries)
    print("관련 키워드:", filter_keywords)

    news_list = []
    seen_urls = set()

    for search_query in fallback_queries:

        if len(news_list) >= max_results:
            break

        params = {
            "apikey": settings.NEWSDATA_API_KEY,
            "country": "kr",
            "language": "ko",
            "q": search_query,
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"뉴스 API 호출 실패 (검색어: {search_query}):", e)
            continue

        print("===== 뉴스 API 응답 =====")
        print("검색어:", search_query)
        print("전체 결과 수:", len(data.get("results", [])))

        for item in data.get("results", []):

            if len(news_list) >= max_results:
                break

            description = item.get("description") or ""
            content = item.get("content") or ""

            if content == "ONLY AVAILABLE IN PAID PLANS":
                text = description
            else:
                text = content if content else description

            if not text:
                continue

            article_url = item.get("link")

            if not article_url:
                continue

            if article_url in seen_urls:
                continue

            # 모든 검색 결과에 동일하게 관련성 검사 적용
            article_text = _normalize(" ".join([
                item.get("title") or "",
                description,
                content if content != "ONLY AVAILABLE IN PAID PLANS" else "",
            ]))

            matched_keywords = [
                keyword
                for keyword in filter_keywords
                if _normalize(keyword) in article_text
            ]

            if matched_keywords:
                print(
                    "관련 기사 통과:",
                    item.get("title"),
                    "| 일치 키워드:",
                    matched_keywords
                )

            elif not description and not content:
                # 기사 내용 자체가 거의 없는 경우에만 일단 후보 유지
                print(
                    "기사 정보 부족 → 후보 유지:",
                    item.get("title")
                )

            else:
                print(
                    "관련성 낮음 → 제외:",
                    item.get("title")
                )
                continue

            seen_urls.add(article_url)

            original_estimated_minutes = max(
                1,
                math.ceil(len(text) / 400)
            )

            news_list.append({
                "title": item.get("title"),
                "description": description,
                "content": text,
                "source": item.get("source_name"),
                "url": article_url,
                "image_url": item.get("image_url"),
                "original_estimated_minutes": original_estimated_minutes,
                "estimated_minutes": original_estimated_minutes,
            })

        print("현재 저장한 뉴스 수:", len(news_list))

    print("===== 최종 뉴스 후보 =====")
    print("최종 저장한 뉴스 수:", len(news_list))

    return news_list