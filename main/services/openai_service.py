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
    search_target,
    target_minutes
):
    prompt = f"""
    너는 사용자의 취향에 맞는 콘텐츠를 찾기 위한
    검색 API용 검색어를 생성하는 역할이다.

    [사용자 상황]
    {situation}

    [사용자 관심사]
    {", ".join(interests)}

    [사용자가 선택한 콘텐츠 유형]
    {content_type}

    [실제로 검색할 콘텐츠 종류]
    {search_target}

    [사용 가능 시간]
    약 {target_minutes}분

    [작업]
    사용자의 관심사와 상황을 참고하여
    검색 API에 바로 사용할 수 있는 한국어 검색어 1개를 만들어라.

    검색어는 실제 검색 결과가 많이 나올 수 있도록
    너무 길거나 문장 형태로 만들지 말고,
    핵심 주제를 나타내는 2~5개의 키워드로 구성한다.

    사용 가능 시간이나 사용자의 상황은
    검색어에 그대로 넣지 말고 콘텐츠를 선택하는 기준으로만 활용한다.

    [콘텐츠 종류별 기준]

    - 읽기 콘텐츠:
    사용자의 관심사를 실제 뉴스 기사에서 검색할 수 있는
    일반적인 핵심 키워드로 변환한다.

    "마음-틈", "몸-틈", "준비-틈",
    "멘탈 케어", "트렌드·이슈"처럼
    서비스 내부에서 사용하는 표현을 그대로 검색어로 사용하지 않는다.

    검색어는 실제 뉴스에 자주 등장할 가능성이 높은
    구체적인 키워드 1개로 만든다.

    예:
    멘탈 케어 → 스트레스, 심리, 불안, 수면
    건강 → 건강, 운동, 질병, 식단
    트렌드·이슈 → 사회, 기술, 문화, 소비
    휴식 → 수면, 여가, 취미, 여행

    "뉴스", "기사", "읽기", "30분", "이동 중" 같은
    콘텐츠 형식이나 시간·상황 표현은 검색어에 넣지 않는다.

    - 유튜브:
    사용자가 실제로 시청하거나 따라 할 수 있는
    영상 콘텐츠를 찾기 위한 핵심 키워드를 만든다.
    필요하면 활동명이나 주제명을 구체적으로 포함한다.

    [출력 규칙]
    검색어만 출력한다.
    설명하지 않는다.
    문장으로 작성하지 않는다.
    따옴표와 번호를 사용하지 않는다.
    검색 API에 바로 전달할 수 있는 한국어 키워드 한 줄만 출력한다.
    """

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    result = response.output_text.strip()

    # 쉼표가 있으면 첫 번째 키워드만 사용
    result = result.split(",")[0].strip()

    # 줄바꿈이 있으면 첫 번째 줄만 사용
    result = result.split("\n")[0].strip()

    # 공백이 여러 개면 첫 번째 단어만 사용
    result = result.split()[0]

    return result
    


def generate_user_search_queries(user):

    context = get_user_context(user)

    interests = (
        context["categories"]
        + context["topics"]
    )

    situation = context["main_situation"]

    if context["other_content"]:
        situation = context["other_content"]

    queries = {}

    for content_type in context["content_types"]:

        if content_type == "독서":
            search_target = "읽기 콘텐츠"
        else:
            search_target = "유튜브"

        query = generate_search_query(
            situation=situation,
            interests=interests,
            content_type=content_type,
            search_target=search_target,
            target_minutes=context["target_minutes"]
        )

        queries[content_type] = query

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

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text.strip()


def get_recommended_contents(user):

    queries = generate_user_search_queries(user)

    news_contents = []
    youtube_contents = []

    for content_type, query in queries.items():

        if content_type == "독서":
            news_contents.extend(
                get_news(query, max_results=5)
            )

        elif content_type in ["듣기", "스트레칭", "마인드컨트롤"]:
            youtube_contents.extend(
                search_youtube(query, max_results=5)
            )

    return {
        "news": news_contents,
        "youtube": youtube_contents,
    }