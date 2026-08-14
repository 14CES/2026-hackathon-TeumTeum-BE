from openai import OpenAI
from django.conf import settings

from onboarding.models import UserProfile
from teumteum.models import MainAnswer

from services.news import get_news
from services.youtube import search_youtube


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


ONBOARDING_CATEGORY_MAP = {
    1: "마음-틈",
    2: "몸-틈",
    3: "준비-틈",
}

ONBOARDING_STATUS_MAP = {
    4: "이동할 때",
    5: "약속 전에",
    6: "휴식할 때",
    7: "업무 및 공부 중에",
}

ONBOARDING_TOPIC_MAP = {
    8: "트렌드·이슈",
    9: "멘탈 케어",
    10: "건강",
    11: "휴식",
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
            "target_minutes": user.target_minutes,
        }

    # 1번 메인 질문 답변
    main_situation = main_answer.situation_option.content

    # 2번 메인 질문 답변들
    content_types = list(
        main_answer.preferred_options.values_list(
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
        "target_minutes": user.target_minutes,
    }


def generate_search_query(
    situation,
    interests,
    content_type,
    target_minutes
):
    prompt = f"""
        너는 짧은 여유 시간에 맞는 맞춤 콘텐츠를 추천하기 위해
        검색 API용 검색어를 생성하는 역할을 한다.

        [사용자 상황]
        {situation}

        [사용자 관심사]
        {", ".join(interests)}

        [검색할 콘텐츠 유형]
        {content_type}

        [사용 가능 시간]
        약 {target_minutes}분

        [작업]
        위 사용자 정보를 종합하여 콘텐츠 검색 API에 사용할
        구체적인 한국어 검색어 1개를 생성하라.

        사용자의 현재 상황과 관심사를 우선적으로 반영한다.
        너무 넓거나 추상적인 단어 대신 실제 콘텐츠 검색 결과에서
        관련성이 높은 결과를 얻을 수 있는 구체적인 검색어를 만든다.

        콘텐츠 유형이 뉴스인 경우:
        최신 정보, 이슈, 트렌드와 관련된 콘텐츠를 찾기 적합한
        검색어를 생성한다.

        콘텐츠 유형이 유튜브인 경우:
        사용자가 실제로 시청하거나 따라 할 수 있는 영상 콘텐츠를
        찾기 적합한 검색어를 생성한다.
        사용 가능 시간을 고려하여 지나치게 긴 콘텐츠를 검색하지 않도록 한다.

        [출력 규칙]
        검색어만 출력한다.
        설명이나 추천 이유를 추가하지 않는다.
        따옴표와 번호를 사용하지 않는다.
        검색 API에 바로 전달할 수 있는 한국어 검색어 한 줄만 출력한다.
        """

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text.strip()


def generate_user_search_queries(user):

    context = get_user_context(user)

    interests = (
        context["categories"]
        + context["topics"]
    )

    # 메인 1번 질문 답변이 있으면 우선 사용
    situation = context["main_situation"]

    # 기타를 선택해서 직접 입력한 경우
    if context["other_content"]:
        situation = context["other_content"]

    queries = {}

    for content_type in context["content_types"]:
        query = generate_search_query(
            situation=situation,
            interests=interests,
            content_type=content_type,
            target_minutes=context["target_minutes"]
        )

        queries[content_type] = query

    return queries



def get_recommended_contents(user):

    # 1. 사용자 정보 기반 검색어 생성
    queries = generate_user_search_queries(user)

    news_contents = []
    youtube_contents = []

    # 2. 콘텐츠 유형별로 검색 API 호출
    for content_type, query in queries.items():

        if content_type == "뉴스":
            news_contents = get_news(query)

        elif content_type == "유튜브":
            youtube_contents = search_youtube(query)

    return {
        "news": news_contents,
        "youtube": youtube_contents,
    }