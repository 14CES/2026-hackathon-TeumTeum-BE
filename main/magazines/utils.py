import math
import random
from collections import Counter
from datetime import datetime, timedelta
from django.utils import timezone
from records.models import Record
from teumteum.models import WellnessArticleSource
from services.openai_service import ONBOARDING_TOPIC_MAP, CHARS_PER_MINUTE


def _get_user_topics(user):
    # 온보딩에서 고른 관심 웰니스 주제(피부/몸/마음/수면)를 텍스트로 변환
    profile = getattr(user, 'profile', None)

    if not profile or not profile.preferred_type:
        return []

    topic_ids = profile.preferred_type.get('topics', [])

    return [
        ONBOARDING_TOPIC_MAP[topic_id]
        for topic_id in topic_ids
        if topic_id in ONBOARDING_TOPIC_MAP
    ]


def _summarize(content, max_chars=80):
    content = content or ""

    if len(content) <= max_chars:
        return content

    return content[:max_chars].rstrip() + "…"


def _to_brief_payload(article, reason=None):
    read_minutes = max(1, math.ceil(len(article.content) / CHARS_PER_MINUTE))

    payload = {
        "id": article.id,
        "title": article.title,
        "topic": article.topics[0] if article.topics else "웰니스",
        "read_minutes": read_minutes,
    }

    if reason is not None:
        payload["reason"] = reason
        payload["summary"] = _summarize(article.content)

    return payload


def _pick_discovery_articles(topics, count):
    # DB에 있는 실제 웰니스 원문 중에서 관심 주제에 맞는 것 위주로 골라 발견 탭에 보여준다
    pool = list(WellnessArticleSource.objects.filter(is_active=True))

    if not pool:
        return []

    matched = [article for article in pool if topics and set(article.topics) & set(topics)]
    unmatched = [article for article in pool if article not in matched]

    random.shuffle(matched)
    random.shuffle(unmatched)

    return (matched + unmatched)[:count]


def get_discovery_data(user):
    records = Record.objects.filter(user=user).select_related('course')

    topics = _get_user_topics(user)
    picked = _pick_discovery_articles(topics, count=3)

    # 1. 초기 사용자 처리 (기록이 없을 때)
    if not records.exists():
        if picked:
            featured_brief = _to_brief_payload(picked[0], reason="틈틈을 시작한 당신을 위한 추천")
            recommendations = [_to_brief_payload(article) for article in picked[1:3]]
        else:
            featured_brief = {
                "id": None,
                "title": "하루 5분, 나를 위한 작은 휴식",
                "topic": "휴식",
                "read_minutes": 1,
                "reason": "틈틈을 시작한 당신을 위한 추천",
                "summary": "작은 틈새 시간만으로도 하루의 피로를 비우고 컨디션을 회복할 수 있습니다."
            }
            recommendations = []

        return {
            "is_initial": True,
            "message": "틈틈이 당신을 알아가는 중이에요. 첫 번째 틈을 완성하면, 나에게 가장 잘 맞는 회복 방식을 발견해드릴게요.",
            "featured_brief": featured_brief,
            "recommendations": recommendations,
        }

    # 2. 주간 통계 계산 (월요일 자정 기준)
    now = timezone.now()
    today = timezone.localtime(now).date()
    monday = today - timedelta(days=today.weekday())
    start_of_current_week = timezone.make_aware(datetime.combine(monday, datetime.min.time()))
    start_of_last_week = start_of_current_week - timedelta(days=7)

    this_week_records = records.filter(started_at__gte=start_of_current_week)
    last_week_records = records.filter(started_at__gte=start_of_last_week, started_at__lt=start_of_current_week)

    this_week_min = sum(r.completed_minutes for r in this_week_records)
    last_week_min = sum(r.completed_minutes for r in last_week_records)
    diff_min = this_week_min - last_week_min
    growth_rate = round((diff_min / last_week_min * 100)) if last_week_min > 0 else 0

    exec_count = this_week_records.count()
    completed_count = this_week_records.filter(completed_at__isnull=False).count()
    comp_rate = round((completed_count / exec_count) * 100) if exec_count > 0 else 0

    # 3. 패턴 분석 (최빈 카테고리, 최빈 장소·상태, 평균 시간)
    categories = [r.category for r in records if r.category]
    best_act = Counter(categories).most_common(1)[0][0] if categories else "스트레칭"
    avg_duration = round(sum(r.completed_minutes for r in records) / records.count()) if records.count() > 0 else 5

    places = [r.course.place for r in records if r.course and r.course.place]
    most_frequent_place = Counter(places).most_common(1)[0][0] if places else "정보 없음"

    states = []
    for r in records:
        if r.course and r.course.current_state:
            states.extend(r.course.current_state)
    most_frequent_state = Counter(states).most_common(1)[0][0] if states else "정보 없음"

    return {
        "is_initial": False,
        "weekly_summary": {
            "current_week_minutes": this_week_min,
            "previous_week_minutes": last_week_min,
            "diff_minutes": diff_min,
            "growth_rate": growth_rate,
            "execution_count": exec_count,
            "completion_rate": comp_rate
        },
        "ai_insight": {
            "summary_text": f"이번 주에는 ‘{best_act}’ 코스를 가장 활발하게 실행했어요. 평균 완료율은 {comp_rate}%입니다.",
            "recommendation_text": "다음 비슷한 틈에는 짧은 호흡과 이완 동작을 먼저 추천할게요."
        },
        "patterns": {
            "most_frequent_place": most_frequent_place,
            "most_frequent_state": most_frequent_state,
            "best_activity": best_act,
            "average_duration_minutes": avg_duration
        },
        "next_suggestion": {
            "text": f"최근 '{most_frequent_state}' 상태가 많았어요. 다음 틈에는 {avg_duration}분 {best_act} 코스를 추천할게요.",
            "preset": {
                "duration_minutes": avg_duration,
                "place": most_frequent_place,
                "recovery_method": best_act
            }
        },
        "featured_brief": (
            _to_brief_payload(picked[0], reason="최근 실행 패턴을 바탕으로 추천드려요")
            if picked else {
                "id": None,
                "title": "오후 피로를 줄이는 3가지 방법",
                "topic": "피부",
                "read_minutes": 1,
                "reason": "최근 피로함 태그를 자주 선택한 당신에게",
                "summary": "충분한 수분 섭취와 어깨 이완으로 오후 피로를 가볍게 비워보세요."
            }
        ),
        "recommendations": [
            _to_brief_payload(article) for article in picked[1:3]
        ],
    }