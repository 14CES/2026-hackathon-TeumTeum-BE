import math
import random
import re

from openai import OpenAI
from django.conf import settings

from onboarding.models import UserProfile
from teumteum.models import MainAnswer, CourseContent, CourseExecution, WellnessArticleSource

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

CHARS_PER_MINUTE = 400

YOUTUBE_SEARCH_CONTENT_TYPES = {
    "듣기",
    "스트레칭",
    "마음 정리",
}

SATISFACTION_SCORES = {
    "good": 1,
    "neutral": 0,
    "bad": -1,
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

    # 최근 평가 이력 (최신순, 최대 5개)
    recent_satisfaction = list(
        CourseExecution.objects
        .filter(user=user)
        .exclude(satisfaction__isnull=True)
        .order_by("-ended_at")
        .values_list("satisfaction", flat=True)[:5]
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
            "recent_satisfaction": recent_satisfaction,
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
        "recent_satisfaction": recent_satisfaction,
        "target_minutes": user.target_minutes,
    }


def get_topic_satisfaction_scores(user):
    """
    평가가 달린 지난 코스의 읽기 콘텐츠 주제(topics)별로
    좋았어요/보통이에요/별로예요 평가를 점수로 합산한다.
    """

    scores = {}

    rated_executions = (
        CourseExecution.objects
        .filter(user=user)
        .exclude(satisfaction__isnull=True)
        .select_related("course")
    )

    for execution in rated_executions:

        score = SATISFACTION_SCORES.get(execution.satisfaction, 0)

        if score == 0:
            continue

        article_contents = CourseContent.objects.filter(
            course=execution.course,
            content_type="article",
        ).exclude(
            source_article__isnull=True
        ).select_related("source_article")

        for content in article_contents:
            for topic in content.source_article.topics:
                scores[topic] = scores.get(topic, 0) + score

    return scores


def generate_search_queries(
    situation,
    next_schedule,
    current_state,
    interests,
    onboarding_status,
    recent_satisfaction,
    content_type,
    target_minutes
):
    prompt = f"""
너는 사용자의 취향과 지금 상황에 맞는 유튜브 영상을 찾기 위한
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

[최근 코스 만족도 (최근순, 최대 5개)]
{", ".join(recent_satisfaction) if recent_satisfaction else "정보 없음"}

[사용자가 선택한 회복 방식]
{content_type}

[사용 가능 시간]
약 {target_minutes}분

[작업]
사용자의 관심사, 현재 상태, 다음 일정, 장소를 종합적으로 참고하여
검색 API에 사용할 수 있는 한국어 검색어를 5개 만들어라.

특히 [현재 몸·마음 상태]와 [다음 일정]을 우선적으로 반영한다.
예를 들어 "피곤해요"가 포함되면 피로 회복·에너지 충전 관련 키워드를,
"몸이 뻐근해요"가 포함되면 스트레칭·이완 관련 키워드를,
"긴장돼요"나 다음 일정이 "약속"이면 마음을 편안하게 하는 키워드를 우선 고려한다.

[최근 코스 만족도]에 "bad"가 많다면 최근과는 다른 새로운 결의 키워드를 시도하고,
"good"이 많다면 비슷한 결의 키워드를 우선 고려한다.

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
    """
    회복 방식 중 유튜브로 찾을 수 있는 유형(듣기/스트레칭/마음 정리)에 대해서만
    검색어를 생성한다. "읽기"는 팀 원문 풀에서 고르므로 검색어가 필요 없다.
    """

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
    recent_satisfaction = context["recent_satisfaction"]

    queries = {}

    for content_type in context["content_types"]:

        if content_type not in YOUTUBE_SEARCH_CONTENT_TYPES:
            continue

        search_queries = generate_search_queries(
            situation=situation,
            next_schedule=next_schedule,
            current_state=current_state,
            interests=interests,
            onboarding_status=onboarding_status,
            recent_satisfaction=recent_satisfaction,
            content_type=content_type,
            target_minutes=context["target_minutes"]
        )

        queries[content_type] = search_queries

    return queries


def _parse_brief_sections(text):
    sections = {"title": "", "body": "", "action": "", "question": ""}

    pattern = r"\[(TITLE|BODY|ACTION|QUESTION)\]"
    parts = re.split(pattern, text)

    for i in range(1, len(parts), 2):
        key = parts[i].lower()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[key] = content

    return sections


def generate_personalized_brief(source_content, source_title, situation, interests, estimated_minutes):
    """
    팀이 쓴 웰니스 원문을 사용자 상황에 맞게 압축·재구성한다.
    제목, 본문, 실천 팁, 짧은 질문을 함께 만든다.
    """

    target_chars = estimated_minutes * CHARS_PER_MINUTE

    prompt = f"""
너는 웰니스 원문을 사용자의 지금 상황에 맞게 짧게 재구성하는 역할이다.

[원문 제목]
{source_title}

[원문]
{source_content}

[사용자 상황]
{situation or "정보 없음"}

[사용자 관심사]
{", ".join(interests) if interests else "정보 없음"}

[목표 분량]
약 {target_chars}자 (읽는 시간 약 {estimated_minutes}분)
최소 {int(target_chars * 0.8)}자 이상, 최대 {int(target_chars * 1.2)}자 이하로 작성한다.

[작업]
1. 사용자 상황과 관심사에 맞춘 제목을 새로 만든다.
2. 원문의 핵심 내용을 목표 분량에 맞게 압축한다. 마크다운은 쓰지 않는다.
3. 지금 바로 할 수 있는 실천 한 가지를 한 문장으로 만든다.
4. 사용자에게 짧게 던질 질문을 한 문장 만든다.

[출력 형식]
아래 마커를 그대로 사용해 순서대로 출력한다. 다른 설명은 추가하지 않는다.

[TITLE]
(제목)
[BODY]
(본문)
[ACTION]
(실천 한 가지)
[QUESTION]
(질문)
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
        sections = _parse_brief_sections(response.output_text.strip())
    except Exception as e:
        print("웰니스 브리프 생성 실패, 원문 사용:", e)
        sections = {}

    return {
        "title": sections.get("title") or source_title,
        "content": sections.get("body") or source_content[:target_chars],
        "action_tip": sections.get("action") or None,
        "question": sections.get("question") or None,
    }


def generate_original_brief(situation, interests, current_state, estimated_minutes):
    """
    팀 원문 풀에 안 본 것이 더 없을 때, 재사용 대신 AI가 처음부터 새로 쓰는 웰니스 브리프.
    형식은 generate_personalized_brief와 동일하다.
    """

    target_chars = estimated_minutes * CHARS_PER_MINUTE

    prompt = f"""
너는 웰니스 코치이자 에디터다. 사용자의 지금 상황에 맞는 웰니스 읽을거리를 처음부터 새로 쓴다.

[사용자 상황]
{situation or "정보 없음"}

[사용자 관심사]
{", ".join(interests) if interests else "정보 없음"}

[현재 몸·마음 상태]
{", ".join(current_state) if current_state else "정보 없음"}

[목표 분량]
약 {target_chars}자 (읽는 시간 약 {estimated_minutes}분)
최소 {int(target_chars * 0.8)}자 이상, 최대 {int(target_chars * 1.2)}자 이하로 작성한다.

[작업]
1. 사용자 관심사와 현재 상태에 맞는 웰니스 주제를 하나 정하고, 그에 맞춘 제목을 만든다.
2. 그 주제에 대해 일반적으로 알려진 사실과 조언을 바탕으로 본문을 새로 쓴다.
   특정 기사나 문헌을 인용하지 않는다. 과장되거나 검증되지 않은 의학적 주장은 하지 않는다.
   마크다운은 쓰지 않는다.
3. 지금 바로 할 수 있는 실천 한 가지를 한 문장으로 만든다.
4. 사용자에게 짧게 던질 질문을 한 문장 만든다.

[출력 형식]
아래 마커를 그대로 사용해 순서대로 출력한다. 다른 설명은 추가하지 않는다.

[TITLE]
(제목)
[BODY]
(본문)
[ACTION]
(실천 한 가지)
[QUESTION]
(질문)
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
        sections = _parse_brief_sections(response.output_text.strip())
    except Exception as e:
        print("AI 원문 생성 실패:", e)
        sections = {}

    return {
        "title": sections.get("title") or "오늘의 웰니스 브리프",
        "content": sections.get("body") or "잠시 숨을 고르고, 지금 몸과 마음의 상태를 가만히 살펴보세요.",
        "action_tip": sections.get("action") or None,
        "question": sections.get("question") or None,
    }


def generate_next_prep_brief(next_schedule, situation, estimated_minutes):
    """
    이 틈이 끝나면 이어질 다음 일정(next_schedule)을 앞두고,
    짧게 마음을 다잡을 수 있는 준비 멘트와 성찰 질문을 만든다.
    형식은 generate_personalized_brief와 동일하다.
    """

    target_chars = estimated_minutes * CHARS_PER_MINUTE

    prompt = f"""
너는 웰니스 코치다. 사용자는 지금 짧은 틈새 시간을 보내고 있고, 이 틈이 끝나면 아래 일정을 앞두고 있다.

[다음 일정]
{next_schedule or "정보 없음"}

[사용자 지금 상황]
{situation or "정보 없음"}

[목표 분량]
약 {target_chars}자 (약 {estimated_minutes}분 분량)

[작업]
1. 다음 일정을 더 편안한 마음으로 시작할 수 있도록 짧은 준비 멘트를 쓴다.
   특정 기사나 문헌을 인용하지 않는다. 과장되거나 검증되지 않은 주장은 하지 않는다.
   마크다운은 쓰지 않는다.
2. 지금 바로 해볼 수 있는 준비 행동 한 가지를 한 문장으로 만든다.
3. 사용자가 스스로 돌아볼 수 있는 짧고 개방적인 성찰 질문을 한 문장 만든다.

[출력 형식]
아래 마커를 그대로 사용해 순서대로 출력한다. 다른 설명은 추가하지 않는다.

[TITLE]
(제목)
[BODY]
(준비 멘트)
[ACTION]
(준비 행동 한 가지)
[QUESTION]
(성찰 질문)
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
        sections = _parse_brief_sections(response.output_text.strip())
    except Exception as e:
        print("다음 준비 브리프 생성 실패:", e)
        sections = {}

    return {
        "title": sections.get("title") or "다음 일정 준비하기",
        "content": sections.get("body") or "잠시 숨을 고르고, 다음 일정을 편안한 마음으로 맞이해보세요.",
        "action_tip": sections.get("action") or None,
        "question": sections.get("question") or None,
    }


DEFAULT_GENERATED_MINUTES = 2  # AI가 처음부터 새로 쓸 때 기본으로 잡는 분량


def select_wellness_articles(user, interests, max_count=3):
    """
    관심사에 맞는 웰니스 원문을 이 사용자가 아직 안 본 것 위주로 고른다.
    맞는 원문이 부족하면 관심사 무관하게 안 본 것으로 채우고,
    그래도 부족하면 이미 본 원문을 재사용하는 대신 AI가 그 자리에서 새로 쓰도록
    "needs_generation" 표시가 된 자리를 채워서 반환한다.
    """

    used_ids = set(
        CourseContent.objects.filter(
            course__user=user,
            content_type="article",
        ).exclude(
            source_article__isnull=True
        ).values_list("source_article_id", flat=True)
    )

    pool = list(WellnessArticleSource.objects.filter(is_active=True))

    unused = [article for article in pool if article.id not in used_ids]

    matched = [
        article for article in unused
        if interests and set(article.topics) & set(interests)
    ]
    unmatched = [article for article in unused if article not in matched]

    # 평가 이력에서 좋았던 주제는 앞으로, 별로였던 주제는 뒤로 보낸다
    topic_scores = get_topic_satisfaction_scores(user)

    def satisfaction_score(article):
        return sum(topic_scores.get(topic, 0) for topic in article.topics)

    random.shuffle(matched)
    random.shuffle(unmatched)
    matched.sort(key=satisfaction_score, reverse=True)
    unmatched.sort(key=satisfaction_score, reverse=True)

    # 관심사에 맞는 원문을 우선하되, 부족하면 안 본 나머지로 채운다.
    # 재사용은 하지 않고, 그래도 부족한 자리는 AI가 새로 쓰도록 남겨둔다.
    candidates = (matched + unmatched)[:max_count]

    result = []

    for article in candidates:
        estimated_minutes = max(1, math.ceil(len(article.content) / CHARS_PER_MINUTE))

        result.append({
            "source_article_id": article.id,
            "title": article.title,
            "content": article.content,
            "source": article.source,
            "original_estimated_minutes": estimated_minutes,
            "estimated_minutes": estimated_minutes,
        })

    # 안 본 원문으로 다 못 채우면, 남은 자리는 AI가 새로 쓰도록 표시해둔다
    needed = max_count - len(result)

    for _ in range(needed):
        result.append({
            "source_article_id": None,
            "needs_generation": True,
            "title": None,
            "content": None,
            "source": "틈틈 AI",
            "original_estimated_minutes": DEFAULT_GENERATED_MINUTES,
            "estimated_minutes": DEFAULT_GENERATED_MINUTES,
        })

    return result


def get_recommended_contents(user):

    context = get_user_context(user)

    interests = context["categories"] + context["topics"]

    queries = generate_user_search_queries(user)

    youtube_contents = []

    # 이 사용자가 이전에 추천받은 유튜브 CourseContent (재사용 후보)
    old_youtube_qs = CourseContent.objects.filter(
        course__user=user,
        content_type="youtube"
    ).exclude(
        video_url__isnull=True
    ).exclude(
        video_url=""
    )

    used_youtube_urls = set(
        old_youtube_qs.values_list("video_url", flat=True)
    )

    print("===== 이전 추천 유튜브 =====")
    print("이미 추천한 유튜브 수:", len(used_youtube_urls))

    seen_youtube_urls = set()

    for content_type, search_queries in queries.items():

        for query in search_queries:

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

    print("===== 중복 제거 후 새 유튜브 후보 =====")
    print("새 유튜브 후보 수:", len(youtube_contents))

    # ---- 유튜브가 부족하면 이전 추천에서 재사용 ----

    MIN_YOUTUBE_COUNT = 3

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

    # 분당 모듈 개수 표의 최대치(4개)까지 고를 수 있도록 후보를 충분히 확보한다
    article_contents = select_wellness_articles(user, interests, max_count=4)

    print("===== 최종 후보 =====")
    print("최종 원문 후보 수:", len(article_contents))
    print("최종 유튜브 후보 수:", len(youtube_contents))

    return {
        "articles": article_contents,
        "youtube": youtube_contents,
    }
