from collections import Counter
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum


def _format_hour_range(start_hour):
    # 2시간 단위 구간(예: 14시 시작 -> "오후 2~4시")을 한국어로 바꾼다
    end_hour = (start_hour + 2) % 24

    def to_12h(hour):
        period = "오전" if hour < 12 else "오후"
        display = hour % 12
        if display == 0:
            display = 12
        return period, display

    start_period, start_display = to_12h(start_hour)
    end_period, end_display = to_12h(end_hour)

    if start_period == end_period:
        return f"{start_period} {start_display}~{end_display}시"
    return f"{start_period} {start_display}시~{end_period} {end_display}시"


def get_mypage_dashboard_data(user):
    # 1. 날짜 기준 설정 (이번 주 월요일 자정 / 지난주 월요일 자정)
    now = timezone.now()
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    start_of_current_week = datetime.combine(monday, datetime.min.time())
    start_of_last_week = start_of_current_week - timedelta(days=7)

    # 타임존 활성화 여부에 따라 안전하게 변환
    if timezone.is_aware(timezone.now()):
        start_of_current_week = timezone.make_aware(start_of_current_week)
        start_of_last_week = timezone.make_aware(start_of_last_week)

    # 2. 유저 기록 안전 조회
    user_records = []
    try:
        from records.models import Record
        user_records = Record.objects.filter(user=user)
    except Exception:
        user_records = []

    # 3. 이번 주 / 지난 주 통계 안전 계산
    this_week_min = 0
    last_week_min = 0
    exec_count = 0
    comp_rate = 0

    if user_records:
        try:
            this_week_qs = user_records.filter(started_at__gte=start_of_current_week)
            last_week_qs = user_records.filter(
                started_at__gte=start_of_last_week, 
                started_at__lt=start_of_current_week
            )
            this_week_min = this_week_qs.aggregate(total=Sum('completed_minutes'))['total'] or 0
            last_week_min = last_week_qs.aggregate(total=Sum('completed_minutes'))['total'] or 0

            exec_count = this_week_qs.count()
            if exec_count > 0:
                completed_count = this_week_qs.filter(completed_at__isnull=False).count()
                comp_rate = round((completed_count / exec_count) * 100)
        except Exception:
            pass

    diff_min = this_week_min - last_week_min
    growth_rate = round((diff_min / last_week_min * 100)) if last_week_min > 0 else 0

    # 4. 나의 틈 패턴 분석
    avg_duration = 11
    if user_records and user_records.count() > 0:
        try:
            tot = user_records.aggregate(total=Sum('completed_minutes'))['total'] or 0
            if tot > 0:
                avg_duration = max(1, round(tot / user_records.count()))
        except Exception:
            pass

    categories, places, states = [], [], []
    if user_records:
        for r in user_records:
            if hasattr(r, 'category') and r.category:
                categories.append(str(r.category))
            if hasattr(r, 'course') and r.course:
                if getattr(r.course, 'place', None):
                    places.append(str(r.course.place))
                if getattr(r.course, 'current_state', None):
                    st = r.course.current_state
                    states.extend(st if isinstance(st, list) else [str(st)])

    best_activity = Counter(categories).most_common(1)[0][0] if categories else "스트레칭"
    most_frequent_place = Counter(places).most_common(1)[0][0] if places else "대중교통"
    most_frequent_state = Counter(states).most_common(1)[0][0] if states else "피곤함"

    # 5. 코멘트 및 다음 제안 프리셋
    # best_activity 코스가 실제로 가장 잘 끝난 시간대(2시간 단위)와 그때의 완료율을 계산한다
    # 데이터가 없는 신규 유저는 예시 문구가 자연스럽게 보이도록 기본값을 둔다
    peak_hour_text = "오후 2~4시"
    peak_comp_rate = 92

    if user_records:
        try:
            best_activity_records = [r for r in user_records if str(r.category) == best_activity]

            bucket_stats = {}
            for r in best_activity_records:
                bucket_start = (r.started_at.hour // 2) * 2
                stats = bucket_stats.setdefault(bucket_start, {"total": 0, "completed": 0})
                stats["total"] += 1
                if r.completed_at is not None:
                    stats["completed"] += 1

            if bucket_stats:
                best_bucket, best_stats = max(
                    bucket_stats.items(),
                    key=lambda item: (item[1]["completed"] / item[1]["total"], item[1]["total"])
                )
                peak_comp_rate = round((best_stats["completed"] / best_stats["total"]) * 100)
                peak_hour_text = _format_hour_range(best_bucket)
        except Exception:
            pass

    ai_discovery_text = (
        f"이번 주에는 '{most_frequent_place}'에 {most_frequent_state}을 가장 많이 느꼈어요.\n"
        f"특히 {peak_hour_text}에 {best_activity} 코스의 완료율이 {peak_comp_rate}%로 가장 높았어요.\n"
        f"다음 비슷한 상황에서는 짧은 {best_activity}을 먼저 추천할게요!"
    )

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