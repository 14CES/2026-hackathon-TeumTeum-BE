import math
import random
from collections import Counter
from django.utils import timezone
from records.models import Record
from .models import WellnessArticle
from services.openai_service import (
    get_user_context,
    generate_discovery_recommendation_reason,
    generate_discovery_one_line_summary,
)

# 기본 읽기 시간 계산 기준 (분당 300자)
CHARS_PER_MINUTE = 300


def _get_user_topics(user):
    try:
        context = get_user_context(user)
        topics = context.get("topics", [])
        categories = context.get("categories", [])
        return list(set(topics + categories))
    except Exception:
        profile = getattr(user, 'profile', None)
        if not profile or not profile.preferred_type:
            return []
        if isinstance(profile.preferred_type, dict):
            return list(set(profile.preferred_type.get('topics', []) + profile.preferred_type.get('wellness', [])))
        elif isinstance(profile.preferred_type, list):
            return profile.preferred_type
        return []


def _summarize(content, max_chars=80):
    content = content or ""
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rstrip() + "…"


def _to_brief_payload(article, reason=None):
    read_minutes = article.read_minutes if getattr(article, 'read_minutes', None) else max(1, math.ceil(len(article.content or "") / CHARS_PER_MINUTE))

    payload = {
        "id": article.id,
        "title": article.title,
        "category": article.category,
        "read_minutes": read_minutes,
        "image_url": article.image_url,
    }

    if reason is not None:
        payload["sub_title"] = reason
        payload["summary"] = article.ai_summary if getattr(article, 'ai_summary', None) else _summarize(article.content)

    return payload


def _pick_discovery_articles(user, user_topics, user_state, user_place, count=4):
    pool = list(WellnessArticle.objects.all())
    if not pool:
        return []

    matched_articles = []
    for article in pool:
        score = 0
        # 1. 온보딩 관심 웰니스/콘텐츠 매칭
        target_wellness = getattr(article, 'target_wellness', []) or []
        target_content_types = getattr(article, 'target_content_types', []) or []
        if set(user_topics) & set(target_wellness + target_content_types):
            score += 2

        # 2. 홈화면 현재 상태 매칭
        target_states = getattr(article, 'target_states', []) or []
        if user_state in target_states:
            score += 3

        # 3. 홈화면 현재 장소 매칭
        target_places = getattr(article, 'target_places', []) or []
        if user_place in target_places:
            score += 1

        if score > 0:
            matched_articles.append(article)

    unmatched_articles = [a for a in pool if a not in matched_articles]


    seed_key = f"{timezone.now().date().isoformat()}-{user.guest_uuid}"
    daily_random = random.Random(seed_key)

    daily_random.shuffle(matched_articles)
    daily_random.shuffle(unmatched_articles)

    return (matched_articles + unmatched_articles)[:count]


def generate_ai_recommendation_reason(user, article):

    if not Record.objects.filter(user=user).exists():
        return None

    # [상세 화면 상단] AI 역할: 당신에게 추천한 이유 생성
    return generate_discovery_recommendation_reason(
        user=user,
        article_title=article.title,
        article_category=article.category
    )


def generate_ai_summary(article):

    # [상세 화면 하단] AI 역할: 틈틈 한 줄 정리 생성

    if getattr(article, 'ai_summary', None) and article.ai_summary.strip():
        return article.ai_summary

    return generate_discovery_one_line_summary(
        article_title=article.title,
        article_content=article.content
    )


def get_discovery_data(user):

    records = Record.objects.filter(user=user).select_related('course')
    topics = _get_user_topics(user)

    # 최근 질문 답변/기록에서 상태 및 장소 파악
    recent_state = "피곤해요"
    recent_place = "이동 중"

    try:
        context = get_user_context(user)
        if context.get("current_state"):
            recent_state = context["current_state"][0]
        if context.get("main_situation"):
            recent_place = context["main_situation"]
    except Exception:
        recent_record = records.order_by('-started_at').first()
        if recent_record and hasattr(recent_record, 'course') and recent_record.course:
            if getattr(recent_record.course, 'current_state', None):
                recent_state = recent_record.course.current_state[0] if isinstance(recent_record.course.current_state, list) else recent_record.course.current_state
            if getattr(recent_record.course, 'place', None):
                recent_place = recent_record.course.place

    picked = _pick_discovery_articles(user, topics, recent_state, recent_place, count=5)

    # 1. 기록이 없는 신규 유저 또는 초기 응답
    if not records.exists():
        if picked:
            featured_brief = _to_brief_payload(picked[0], reason="틈틈을 시작한 당신을 위한 추천")
            recommendations = [_to_brief_payload(article) for article in picked[1:5]]
        else:
            featured_brief = {
                "id": None,
                "title": "오후 피로를 줄이는 3가지 방법",
                "category": "건강",
                "read_minutes": 1,
                "sub_title": "틈틈을 시작한 당신을 위한 추천",
                "summary": "작은 틈새 시간만으로도 하루의 피로를 비우고 컨디션을 회복할 수 있습니다.",
                "image_url": ""
            }
            recommendations = []

        return {
            "is_initial": True,
            "message": "틈틈이 당신을 알아가는 중이에요. 첫 번째 틈을 완성하면, 나에게 가장 잘 맞는 회복 방식을 발견해드릴게요.",
            "featured": featured_brief,
            "recommendations": recommendations,
        }

    # 2. 기존 유저 (맞춤형 추천 데이터 반환)
    featured_reason = f"최근 '{recent_state}' 상태를 자주 느낀 당신에게"
    featured_brief = _to_brief_payload(picked[0], reason=featured_reason) if picked else None
    recommendations = [_to_brief_payload(article) for article in picked[1:5]] if len(picked) > 1 else []

    return {
        "is_initial": False,
        "featured": featured_brief,
        "recommendations": recommendations,
    }