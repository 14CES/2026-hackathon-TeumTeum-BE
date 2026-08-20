from collections import Counter
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum


# 코드/ID 매핑 테이블
PLACE_MAP = {
    1: "이동 중", 2: "카페·실내", 3: "학교·회사", 4: "집", 5: "기타",
    "1": "이동 중", "2": "카페·실내", "3": "학교·회사", "4": "집", "5": "기타"
}
STATE_MAP = {
    1: "피곤함", 2: "긴장됨", 3: "머릿속이 복잡함", 4: "몸이 뻐근함", 5: "피부가 신경 쓰임",
    "1": "피곤함", "2": "긴장됨", "3": "머릿속이 복잡함", "4": "몸이 뻐근함", "5": "피부가 신경 쓰임",
    "피곤해요": "피곤함", "긴장돼요": "긴장됨", "복잡해요": "머릿속이 복잡함", "몸이 뻐근해요": "몸이 뻐근함"
}
CATEGORY_MAP = {
    "BODY": "스트레칭", "MIND": "마음 정리", "PREP": "준비-틈", "READ": "읽기",
    1: "읽기", 2: "듣기", 3: "스트레칭", 4: "마음 정리",
    "1": "읽기", "2": "듣기", "3": "스트레칭", "4": "마음 정리"
}

# 유효한 활동 카테고리 (긴 뉴스/아티클 제목 유입 방지)
VALID_ACTIVITIES = {"스트레칭", "마음 정리", "읽기", "듣기", "준비-틈"}


def _format_hour_range(start_hour):
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
    now = timezone.now()
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    start_of_current_week = datetime.combine(monday, datetime.min.time())
    start_of_last_week = start_of_current_week - timedelta(days=7)

    if timezone.is_aware(now):
        start_of_current_week = timezone.make_aware(start_of_current_week)
        start_of_last_week = timezone.make_aware(start_of_last_week)

    # 1. 유저 기록 조회
    user_records = []
    try:
        from records.models import Record
        user_records = Record.objects.filter(user=user).select_related('course')
    except Exception:
        user_records = []

    # 2. 이번 주 / 지난 주 통계 계산
    this_week_min = 0
    last_week_min = 0
    exec_count = 0
    comp_rate = 0

    has_records = user_records and user_records.exists()

    if has_records:
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

    # 3. 평균 틈 시간 계산 (기록 없으면 None)
    avg_duration = None
    if has_records:
        try:
            tot = user_records.aggregate(total=Sum('completed_minutes'))['total'] or 0
            count = user_records.count()
            if count > 0 and tot > 0:
                avg_duration = max(1, round(tot / count))
        except Exception:
            pass

    # 4. 홈 화면 입력값/기록에서 패턴 추출
    categories, places, states = [], [], []

    # A. Record에서 추출
    if has_records:
        for r in user_records:
            # 1) 활동 카테고리 검증 및 매핑
            cat = getattr(r, 'category', None) or getattr(r, 'course_type', None)
            if cat:
                cat_list = cat if isinstance(cat, list) else str(cat).split(",")
                for c in cat_list:
                    mapped_cat = CATEGORY_MAP.get(c, str(c))
                    # 유효한 활동 카테고리만 추가 (아티클 제목 등 제외)
                    if mapped_cat in VALID_ACTIVITIES:
                        categories.append(mapped_cat)

            # 2) 장소 추출
            place = getattr(r, 'place', None) or (getattr(r.course, 'place', None) if getattr(r, 'course', None) else None)
            if place:
                places.append(PLACE_MAP.get(place, str(place)))

            # 3) 상태 추출
            st = getattr(r, 'current_state', None) or (getattr(r.course, 'current_state', None) if getattr(r, 'course', None) else None)
            if st:
                st_list = st if isinstance(st, list) else [st]
                for item in st_list:
                    states.append(STATE_MAP.get(item, str(item)))

    # B. 코스 기록이 없을 때 홈 질문 답변(MainAnswer)에서 장소/상태 참조
    if not places or not states:
        try:
            from main.models import MainAnswer
            main_answers = MainAnswer.objects.filter(user=user)
            for ma in main_answers:
                if hasattr(ma, 'place_option') and ma.place_option:
                    places.append(PLACE_MAP.get(ma.place_option, str(ma.place_option)))
                if hasattr(ma, 'current_state_options') and ma.current_state_options:
                    opts = ma.current_state_options if isinstance(ma.current_state_options, list) else [ma.current_state_options]
                    for opt in opts:
                        states.append(STATE_MAP.get(opt, str(opt)))
        except Exception:
            pass

    # C. 최빈값 산출 (기록/선택이 없으면 null(None) 처리)
    best_activity = Counter(categories).most_common(1)[0][0] if categories else None
    most_frequent_place = Counter(places).most_common(1)[0][0] if places else None
    most_frequent_state = Counter(states).most_common(1)[0][0] if states else None

    # 5. 피크 시간대 분석
    peak_hour_text = None
    peak_comp_rate = None

    if has_records and best_activity:
        try:
            def _record_categories(r):
                cat = getattr(r, 'category', None)
                if not cat:
                    return []
                cat_list = cat if isinstance(cat, list) else str(cat).split(",")
                return [CATEGORY_MAP.get(c, str(c)) for c in cat_list]

            best_activity_records = [
                r for r in user_records
                if best_activity in _record_categories(r)
            ]

            bucket_stats = {}
            for r in best_activity_records:
                if r.started_at:
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

    # 6. AI 요약 텍스트 및 추천 구성
    if exec_count == 0 or not best_activity:
        place_guide = f"‘{most_frequent_place}’에서 " if most_frequent_place else ""
        state_guide = f"{most_frequent_state} 상태일 때 " if most_frequent_state else ""
        ai_discovery_text = (
            f"아직 완료한 틈 코스가 없어요.\n"
            f"오늘 {place_guide}{state_guide}가벼운 코스로 첫 번째 틈을 완성해보세요!"
        )
        suggested_course_title = "첫 번째 틈 코스를 시작해보세요"
        suggested_course_desc = "나에게 맞는 짧은 틈새 회복을 추천해 드릴게요."
        suggested_course_name = "가벼운 리셋 코스"
        suggested_time = avg_duration if avg_duration else 5
    else:
        ai_discovery_text = (
            f"이번 주에는 ‘{most_frequent_place or '일상'}’에 {most_frequent_state or '피로'}을 가장 많이 느꼈어요.\n"
            f"특히 {peak_hour_text or '오후 시간대'}에 {best_activity} 코스의 완료율이 {peak_comp_rate or 100}%로 가장 높았어요.\n"
            f"다음 비슷한 상황에서는 짧은 {best_activity}을 먼저 추천할게요!"
        )
        suggested_time = min(max(avg_duration or 5, 3), 15)
        suggested_course_name = f"{suggested_time}분 {best_activity} 코스"
        suggested_course_title = f"최근 {most_frequent_place or '자주 머무는 곳'}에서 피로도가 높았어요."
        suggested_course_desc = f"다음에 비슷한 틈이 생기면 {suggested_course_name}를 먼저 추천할게요!"

    next_suggestion = {
        "title": suggested_course_title,
        "description": suggested_course_desc,
        "preset": {
            "target_minutes": suggested_time,
            "place": most_frequent_place,
            "recovery_method": best_activity,
            "course_name": suggested_course_name
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