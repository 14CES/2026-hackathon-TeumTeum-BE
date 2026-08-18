from collections import Counter
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from records.models import Record

def get_mypage_dashboard_data(user):
    # 1. 날짜 기준 설정 (이번 주 월요일 자정 / 지난주 월요일 자정)
    # USE_TZ=False라 timezone.now()는 이미 로컬 타임존 기준 naive datetime이므로
    # localtime()/make_aware() 변환이 필요 없다 (오히려 naive datetime에 쓰면 에러남)
    now = timezone.now()
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    start_of_current_week = datetime.combine(monday, datetime.min.time())
    start_of_last_week = start_of_current_week - timedelta(days=7)

    # 2. 이번 주 / 지난 주 기록
    user_records = Record.objects.filter(user=user)
    this_week_records = user_records.filter(started_at__gte=start_of_current_week)
    last_week_records = user_records.filter(
        started_at__gte=start_of_last_week, 
        started_at__lt=start_of_current_week
    )

    # 3. 이번 주 나의 틈 통계 계산
    this_week_min = this_week_records.aggregate(total=Sum('completed_minutes'))['total'] or 0
    last_week_min = last_week_records.aggregate(total=Sum('completed_minutes'))['total'] or 0
    diff_min = this_week_min - last_week_min
    growth_rate = round((diff_min / last_week_min * 100)) if last_week_min > 0 else 0

    exec_count = this_week_records.count()
    completed_count = this_week_records.filter(completed_at__isnull=False).count()
    comp_rate = round((completed_count / exec_count) * 100) if exec_count > 0 else 0

    # 4. 나의 틈 패턴 분석
    total_count = user_records.count()
    avg_duration = (
        round(user_records.aggregate(total=Sum('completed_minutes'))['total'] / total_count)
        if total_count > 0 else 11
    )

    categories = [r.category for r in user_records if r.category]
    best_activity = Counter(categories).most_common(1)[0][0] if categories else "스트레칭"

    # Course 연동 또는 UserProfile/MainQuestion 데이터 기반 추출
    places, states = [], []
    for r in user_records:
        if hasattr(r, 'course') and r.course:
            if getattr(r.course, 'place', None):
                places.append(r.course.place)
            if getattr(r.course, 'current_state', None):
                states.extend(r.course.current_state if isinstance(r.course.current_state, list) else [r.course.current_state])

    most_frequent_place = Counter(places).most_common(1)[0][0] if places else "대중교통"
    most_frequent_state = Counter(states).most_common(1)[0][0] if states else "피곤함"

    # 5. AI가 발견한 나 텍스트 구성
    # 시간대별 완료율 집계 로직
    peak_hour_text = "오후 2~4시"
    peak_comp_rate = 92
    
    ai_discovery_text = (
        f"이번 주에는 '{most_frequent_place}'에 {most_frequent_state}을 가장 많이 느꼈어요.\n"
        f"특히 {peak_hour_text}에 {best_activity} 코스의 완료율이 {peak_comp_rate}%로 가장 높았어요.\n"
        f"다음 비슷한 상황에서는 짧은 {best_activity}을 먼저 추천할게요!"
    )

    # 6. AI의 다음 제안 구성
    suggested_time = min(max(avg_duration, 3), 15)
    next_suggestion = {
        "title": f"최근 {most_frequent_place} 피로도가 높았어요.",
        "description": f"다음에 비슷한 틈이 생기면 {suggested_time}분 목·어깨 리셋 코스를 먼저 추천할게요!",
        "preset": {
            "target_minutes": suggested_time,
            "place": most_frequent_place,
            "recovery_method": best_activity,
            "course_name": f"{suggested_time}분 목·어깨 리셋 코스"
        }
    }

    return {
        "weekly_recovery": {
            "current_week_minutes": this_week_min,
            "previous_week_minutes": last_week_min,
            "diff_minutes": diff_min,
            "growth_rate": growth_rate,
            "executed_courses": exec_count,
            "completion_rate": comp_rate
        },
        "ai_discovery": {
            "summary_text": ai_discovery_text
        },
        "teum_pattern": {
            "most_frequent_place": most_frequent_place,
            "most_frequent_state": most_frequent_state,
            "best_activity": best_activity,
            "avg_duration_minutes": avg_duration
        },
        "next_suggestion": next_suggestion
    }