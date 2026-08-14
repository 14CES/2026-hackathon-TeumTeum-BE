import requests
from django.conf import settings

TOPIC_KEYWORD_MAP = {
    "트렌드 토픽": "트렌드",
    "멘탈 케어": "힐링",
    "운동": "건강",
    "휴식": "휴식",
}

def fetch_recommended_news(user_interest=None):
    url = "https://newsdata.io/api/1/latest"
    
    # 관심사가 없거나 매핑이 안되면 기본값 '뉴스'
    query_keyword = TOPIC_KEYWORD_MAP.get(user_interest, "뉴스")
    api_key = getattr(settings, 'NEWSDATA_API_KEY', None)

    print("\n========== [NewsData API 디버깅 시작] ==========")
    print(f"1. API KEY 존재 여부: {bool(api_key)}")
    print(f"2. 전달된 유저 관심사: '{user_interest}' -> 변환된 키워드: '{query_keyword}'")

    if api_key:
        params = {
            "apikey": api_key,
            "country": "kr",
            "language": "ko",
            "q": query_keyword,
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            print(f"3. HTTP 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"4. 검색 결과 기사 수: {len(results)}개")
                
                if results:
                    news = results[0]
                    raw_content = news.get("description") or news.get("content") or "내용 없음"
                    content_snippet = raw_content[:150] + "..." if len(raw_content) > 150 else raw_content
                    estimated_minutes = max(1, round(len(raw_content) / 300))

                    print(f"✅ 외부 뉴스 로드 성공! 기사 제목: {news.get('title')}")
                    print("=================================================\n")

                    return {
                        "title": news.get("title", "오늘의 추천 매거진"),
                        "content_type": "매거진",
                        "read_minutes": estimated_minutes,
                        "content": content_snippet,
                        "content_url": news.get("link", "https://example.com/magazine/1")
                    }
                else:
                    print("⚠️ 200 OK 응답을 받았으나 해당 키워드의 뉴스 결과가 0건입니다.")
            else:
                print(f"❌ API 요청 실패 응답: {response.text}")
        except Exception as e:
            print(f"❌ Exception 발생: {e}")

    print("⚠️ 외부 API 통신 불가능으로 인한 백업(Fallback) 응답 반환")
    print("=================================================\n")

    # API 호출 실패 시 반환되는 백업 데이터
    return {
        "title": f"하루 5분, 나를 위한 작은 휴식 ({user_interest or '기본'} 맞춤)",
        "content_type": "매거진",
        "read_minutes": 5,
        "content": "바쁜 하루 속 잠시 멈추고 나를 돌아보는 시간에 대한 이야기입니다.",
        "content_url": "https://example.com/magazine/1"
    }