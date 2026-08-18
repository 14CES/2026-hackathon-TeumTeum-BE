from collections import Counter
from datetime import datetime, timedelta
from django.utils import timezone
from records.models import Record

# 장소/상태 코드 매핑
PLACE_MAP = {1: "이동 중", 2: "카페·실내", 3: "학교·회사", 4: "집", 5: "기타"}
STATE_MAP = {1: "피곤해요", 2: "긴장돼요", 3: "복잡해요", 4: "몸이 뻐근해요", 5: "피부가 신경 쓰여요"}

def get_discovery_data(user):
    records = Record.objects.filter(user=user)
    
    # 1. 초기 사용자 처리 (기록이 없을 때)
    if not records.exists():
        # 온보딩 관심 주제
        preferred = getattr(user, 'profile', None)
        topic_id = preferred.preferred_type.get('topics', [9])[0] if preferred and preferred.preferred_type else 9
        
        return {
            "is_initial": True,
            "message": "틈틈이 당신을 알아가는 중이에요. 첫 번째 틈을 완성하면, 나에게 가장 잘 맞는 회복 방식을 발견해드릴게요.",
            "featured_brief": {
                "id": 1,
                "title": "하루 5분, 나를 위한 작은 휴식",
                "topic": "휴식",
                "read_minutes": 1,
                "reason": "틈틈을 시작한 당신을 위한 추천",
                "summary": "작은 틈새 시간만으로도 하루의 피로를 비우고 컨디션을 회복할 수 있습니다."
            },
            "recommendations": [
                {"id": 2, "title": "출퇴근길 가벼운 목 스트레칭", "topic": "몸", "read_minutes": 1},
                {"id": 3, "title": "도파민 디톡스를 위한 1분 호흡", "topic": "마음", "read_minutes": 1}
            ]
        }

    # 2. 주간 통계 계산 (월요일 기준)
    now = timezone.now()
    start_of_current_week = now - timedelta(days=now.weekday())
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

    # 3. 패턴 분석 (최빈 카테고리 및 평균 시간)
    categories = [r.category for r in records if r.category]
    best_act = Counter(categories).most_common(1)[0][0] if categories else "스트레칭"
    avg_duration = round(sum(r.completed_minutes for r in records) / records.count()) if records.count() > 0 else 5

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
            "most_frequent_place": "이동 중",
            "most_frequent_state": "피곤함",
            "best_activity": best_act,
            "average_duration_minutes": avg_duration
        },
        "next_suggestion": {
            "text": f"최근 피로도가 높았어요. 다음 틈에는 {avg_duration}분 {best_act} 코스를 추천할게요.",
            "preset": {
                "duration_minutes": avg_duration,
                "place": "이동 중",
                "recovery_method": best_act
            }
        },
        "featured_brief": {
            "id": 1,
            "title": "오후 피로를 줄이는 3가지 방법",
            "topic": "피부",
            "read_minutes": 1,
            "reason": "최근 피로함 태그를 자주 선택한 당신에게",
            "summary": "충분한 수분 섭취와 어깨 이완으로 오후 피로를 가볍게 비워보세요."
        },
        "recommendations": [
            {"id": 2, "title": "출퇴근길 목·어깨를 가볍게 하는 스트레칭", "topic": "몸", "read_minutes": 1},
            {"id": 3, "title": "잠깐의 호흡이 스트레스를 줄이는 과학적 이유", "topic": "마음", "read_minutes": 2}
        ]
    }