import random
from openai import OpenAI
from django.conf import settings

from onboarding.models import UserProfile
from teumteum.models import MainAnswer,CourseContent

from services.news import get_news
from services.youtube import search_youtube


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


ONBOARDING_CATEGORY_MAP = {
    1: "읽기",
    2: "듣기",
    3: "스트레칭",
    4: "마음 정리",
}

ONBOARDING_STATUS_MAP = {
    5: "이동 중",
    6: "약속 전",
    7: "휴식 중",
    8: "업무·수업 중",
}

ONBOARDING_TOPIC_MAP = {
    9: "피부",
    10: "몸",
    11: "마음",
    12: "수면",
}


def get_user_context(user):
    # 온보딩 정보 조회
    profile = UserProfile.objects.get(user=user)

    # JSONField에서 저장된 값 가져오기
    status_ids = profile.status or []
    preferred_type = profile.preferred_type or {}

    category_ids = preferred_type.get("categories", [])
    topic_ids = preferred_type.get("topics", [])

    # 숫자 ID -> 실제 텍스트 변환
    onboarding_status = [
        ONBOARDING_STATUS_MAP[option_id]
        for option_id in status_ids
        if option_id in ONBOARDING_STATUS_MAP
    ]

    categories = [
        ONBOARDING_CATEGORY_MAP[option_id]
        for option_id in category_ids
        if option_id in ONBOARDING_CATEGORY_MAP
    ]

    topics = [
        ONBOARDING_TOPIC_MAP[option_id]
        for option_id in topic_ids
        if option_id in ONBOARDING_TOPIC_MAP
    ]

    # 가장 최근 메인 질문 답변 조회
    main_answer = (
        MainAnswer.objects
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )

    # 메인 질문 답변이 없는 경우
    if not main_answer:
        return {
            "onboarding_status": onboarding_status,
            "categories": categories,
            "topics": topics,
            "main_situation": None,
            "other_content": None,
            "content_types": [],
            "next_schedule": None,
            "next_schedule_other_content": None,
            "current_state": [],
            "target_minutes": user.target_minutes,
        }

    # 1번 질문 답변: 장소
    main_situation = main_answer.situation_option.content

    # 2번 질문 답변: 회복 방식
    content_types = list(
        main_answer.preferred_options.values_list(
            "content",
            flat=True
        )
    )

    # 3번 질문 답변: 다음 일정
    next_schedule = (
        main_answer.next_schedule_option.content
        if main_answer.next_schedule_option
        else None
    )

    # 4번 질문 답변: 현재 상태
    current_state = list(
        main_answer.current_state_options.values_list(
            "content",
            flat=True
        )
    )

    return {
        "onboarding_status": onboarding_status,
        "categories": categories,
        "topics": topics,
        "main_situation": main_situation,
        "other_content": main_answer.other_content,
        "content_types": content_types,
        "next_schedule": next_schedule,
        "next_schedule_other_content": main_answer.next_schedule_other_content,
        "current_state": current_state,
        "target_minutes": user.target_minutes,
    }


def generate_search_queries(
    situation,
    next_schedule,
    current_state,
    interests,
    onboarding_status,
    content_type,
    search_target,
    target_minutes
):
    prompt = f"""
너는 사용자의 취향과 지금 상황에 맞는 콘텐츠를 찾기 위한
검색 API용 검색어를 생성하는 역할이다.

[사용자가 있는 장소]
{situation}

[다음 일정]
{next_schedule or "정보 없음"}

[현재 몸·마음 상태]
{", ".join(current_state) if current_state else "정보 없음"}

[사용자 관심사 (온보딩에서 선택)]
{", ".join(interests) if interests else "정보 없음"}

[평소 틈이 자주 생기는 순간 (온보딩에서 선택)]
{", ".join(onboarding_status) if onboarding_status else "정보 없음"}

[사용자가 선택한 콘텐츠 유형]
{content_type}

[실제로 검색할 콘텐츠 종류]
{search_target}

[사용 가능 시간]
약 {target_minutes}분

[작업]
사용자의 관심사, 현재 상태, 다음 일정, 장소를 종합적으로 참고하여
검색 API에 사용할 수 있는 한국어 검색어를 5개 만들어라.

특히 [현재 몸·마음 상태]와 [다음 일정]을 우선적으로 반영한다.
예를 들어 "피곤해요"가 포함되면 피로 회복·에너지 충전 관련 키워드를,
"몸이 뻐근해요"가 포함되면 스트레칭·이완 관련 키워드를,
"긴장돼요"나 다음 일정이 "약속"이면 마음을 편안하게 하는 키워드를 우선 고려한다.

각 검색어는 서로 다른 주제이지만
사용자의 관심사와 관련되어야 한다.

각 검색어는 반드시 공백 없는
일반적인 한국어 핵심 키워드 1개로만 작성한다.

검색 결과가 많이 나올 수 있는
넓고 일반적인 단어를 사용한다.

두 개 이상의 단어를 조합하지 않는다.

예를 들어
"스트레스 관리", "불안 증상", "수면 개선"처럼
여러 단어로 이루어진 검색어를 만들지 않는다.

"마음 치유 책"처럼 지나치게 구체적인 검색어도 만들지 않는다.

[콘텐츠 종류별 기준]

- 읽기 콘텐츠:
실제 뉴스 기사에서 검색 가능한
구체적이고 일반적인 핵심 키워드를 만든다.

예:
멘탈 케어 → 스트레스, 불안, 수면, 정신건강, 심리, 명상, 마음챙김, 휴식, 웰빙, 자기관리
건강 → 운동, 건강, 식단, 질병, 생활습관, 웰니스, 건강관리, 체력, 피로회복, 스트레칭, 걷기, 요가
휴식 → 휴식, 여가, 힐링, 여행, 취미, 재충전, 웰니스, 라이프스타일
트렌드·이슈 → 사회, 기술, 문화, 소비, 경제, 라이프스타일, 웰니스 트렌드

- 유튜브:
사용자가 실제로 시청하거나 따라 할 수 있는
영상 콘텐츠를 찾기 위한 핵심 키워드를 만든다.

[출력 규칙]
검색어만 출력한다.
설명하지 않는다.
번호를 사용하지 않는다.
각 검색어는 한 줄에 하나씩 출력한다.
정확히 5개의 검색어를 출력한다.
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
    except Exception as e:
        print(f"검색어 생성 실패 ({content_type}):", e)
        return []

    result = response.output_text.strip()

    queries = [
        line.strip()
        for line in result.split("\n")
        if line.strip()
    ]

    return queries[:5]
    


def generate_user_search_queries(user):

    context = get_user_context(user)

    interests = (
        context["categories"]
        + context["topics"]
    )

    situation = context["main_situation"]

    if context["other_content"]:
        situation = context["other_content"]

    next_schedule = context["next_schedule"]

    if context["next_schedule_other_content"]:
        next_schedule = context["next_schedule_other_content"]

    current_state = context["current_state"]
    onboarding_status = context["onboarding_status"]

    queries = {}

    for content_type in context["content_types"]:

        if content_type == "읽기":
            search_target = "읽기 콘텐츠"
        else:
            search_target = "유튜브"

        search_queries = generate_search_queries(
            situation=situation,
            next_schedule=next_schedule,
            current_state=current_state,
            interests=interests,
            onboarding_status=onboarding_status,
            content_type=content_type,
            search_target=search_target,
            target_minutes=context["target_minutes"]
        )

        queries[content_type] = search_queries

    return queries


def summarize_content(text, estimated_minutes):
    """
    기사 본문을 예상 읽기 시간에 맞는 분량으로 요약한다.
    1분당 400자를 기준으로 한다.
    """

    target_chars = estimated_minutes * 400

    # 이미 목표 분량 이하라면 요약하지 않음
    if len(text) <= target_chars:
        return text

    prompt = f"""
    너는 짧은 틈 시간에 읽을 수 있도록 기사 내용을 요약하는 역할을 한다.

    [기사 원문]
    {text}

    [목표 읽기 시간]
    약 {estimated_minutes}분

    [목표 분량]
    약 {target_chars}자

    [작업]
    반드시 목표 글자 수에 최대한 가깝게 작성한다.
    최소 {int(target_chars * 0.8)}자 이상, 최대 {int(target_chars * 1.2)}자 이하를 목표로 한다.

    기사의 핵심 사실, 주요 주장, 중요한 수치와 맥락을 유지한다.
    불필요한 반복이나 장황한 표현만 제거한다.
    내용을 지나치게 압축하지 않는다.

    [출력 규칙]
    요약된 본문만 출력한다.
    제목이나 설명을 추가하지 않는다.
    마크다운을 사용하지 않는다.
    """

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
    except Exception as e:
        print("기사 요약 실패, 원문 사용:", e)
        return text

    return response.output_text.strip()


def get_recommended_contents(user):

    queries = generate_user_search_queries(user)

    news_contents = []
    youtube_contents = []

    # 이 사용자가 이전에 추천받은 뉴스 CourseContent (재사용 후보)
    old_news_qs = CourseContent.objects.filter(
        course__user=user,
        content_type="article"
    ).exclude(
        content_url__isnull=True
    ).exclude(
        content_url=""
    )

    # 이 사용자가 이전에 추천받은 유튜브 CourseContent (재사용 후보)
    old_youtube_qs = CourseContent.objects.filter(
        course__user=user,
        content_type="youtube"
    ).exclude(
        video_url__isnull=True
    ).exclude(
        video_url=""
    )

    used_news_urls = set(
        old_news_qs.values_list("content_url", flat=True)
    )

    used_youtube_urls = set(
        old_youtube_qs.values_list("video_url", flat=True)
    )

    print("===== 이전 추천 콘텐츠 =====")
    print("이미 추천한 뉴스 수:", len(used_news_urls))
    print("이미 추천한 유튜브 수:", len(used_youtube_urls))

    seen_news_urls = set()
    seen_youtube_urls = set()

    for content_type, search_queries in queries.items():

        for query in search_queries:

            if content_type == "읽기":

                results = get_news(query, max_results=5)

                for content in results:
                    url = content.get("url")

                    if not url:
                        continue

                    if url in used_news_urls:
                        continue

                    if url in seen_news_urls:
                        continue

                    seen_news_urls.add(url)
                    news_contents.append(content)

            elif content_type in [
                "듣기",
                "스트레칭",
                "마음 정리"
            ]:

                results = search_youtube(query, max_results=5)

                for content in results:
                    url = content.get("url")

                    if not url:
                        continue

                    if url in used_youtube_urls:
                        continue

                    if url in seen_youtube_urls:
                        continue

                    seen_youtube_urls.add(url)
                    youtube_contents.append(content)

    print("===== 중복 제거 후 새 콘텐츠 후보 =====")
    print("새 뉴스 후보 수:", len(news_contents))
    print("새 유튜브 후보 수:", len(youtube_contents))

    # ---- 여기서부터 재사용 로직 ----

    MIN_NEWS_COUNT = 3
    MIN_YOUTUBE_COUNT = 3

    if len(news_contents) < MIN_NEWS_COUNT:

        needed = MIN_NEWS_COUNT - len(news_contents)

        # 이미 새 후보로 뽑힌 것 제외하고, 이전 콘텐츠 중 랜덤하게 채움
        reusable_news = [
            content for content in old_news_qs
            if content.content_url not in seen_news_urls
            and content.content
        ]

        random.shuffle(reusable_news)

        added = 0

        for old_content in reusable_news:

            if added >= needed:
                break

            news_contents.append({
                "title": old_content.title,
                "description": old_content.description,
                "content": old_content.content,
                "source": old_content.source,
                "url": old_content.content_url,
                "image_url": old_content.image_url,
                "original_estimated_minutes": old_content.estimated_minutes,
                "estimated_minutes": old_content.estimated_minutes,
            })

            seen_news_urls.add(old_content.content_url)
            added += 1

        print(f"뉴스 부족 → 이전 추천 뉴스에서 추가: {added}")

    if len(youtube_contents) < MIN_YOUTUBE_COUNT:

        needed = MIN_YOUTUBE_COUNT - len(youtube_contents)

        reusable_youtube = [
            content for content in old_youtube_qs
            if content.video_url not in seen_youtube_urls
        ]

        random.shuffle(reusable_youtube)

        added = 0

        for old_content in reusable_youtube:

            if added >= needed:
                break

            youtube_contents.append({
                "title": old_content.title,
                "url": old_content.video_url,
                "thumbnail": old_content.thumbnail_url,
                "channel": old_content.channel_name,
                "original_estimated_minutes": old_content.estimated_minutes,
                "estimated_minutes": old_content.estimated_minutes,
            })

            seen_youtube_urls.add(old_content.video_url)
            added += 1

        print(f"유튜브 부족 → 이전 추천 유튜브에서 추가: {added}")

    print("===== 최종 후보 (재사용 포함) =====")
    print("최종 뉴스 후보 수:", len(news_contents))
    print("최종 유튜브 후보 수:", len(youtube_contents))

    return {
        "news": news_contents,
        "youtube": youtube_contents,
    }