from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

# Create your views here.
from .serializers import (
    MainGETSerializer,
    MainSerializer,
    MainAnswerSerializer,
    QuestionSerializer,
    CourseSerializer,
    CourseExecutionSerializer,
    CourseContentSerializer,
    CourseRatingSerializer,
)

from .models import (
    TimeSetting,
    Question,
    Option,
    MainAnswer,
    Course,
    CourseContent,
    CourseExecution,
    WeeklyUsage,
)

from rest_framework import viewsets, status
from rest_framework.response import Response

from services.openai_service import get_user_context, get_recommended_contents, generate_personalized_brief, generate_original_brief, generate_next_prep_brief
from services.course import (
    select_best_contents_in_range,
    get_module_count_range,
    allocate_content_minutes,
    select_activity_module,
    YOUTUBE_CONTENT_TYPES,
)

from accounts.models import User
from onboarding.models import UserProfile
from records.models import Record, RecordContent


def get_week_start(dt):
    # 월요일을 그 주의 시작으로 본다
    date = timezone.localtime(dt).date()
    return date - timedelta(days=date.weekday())


def record_weekly_usage(user, seconds):
    minutes = round(seconds / 60)

    if minutes <= 0:
        return

    week_start = get_week_start(timezone.now())

    weekly_usage, _ = WeeklyUsage.objects.get_or_create(
        user=user,
        week_start=week_start,
    )

    weekly_usage.total_minutes += minutes
    weekly_usage.save()


NEXT_PREP_MINUTES = 1
NEXT_SCHEDULE_SKIP_VALUES = {"없음"}


def pick_next_prep_text(context):
    # 오디오가이드/스트레칭 등 활동 모듈이 이미 자리를 차지했다면 호출하는 쪽에서 이 함수를 부르지 않는다.
    # 다음 일정이 "없음"이거나 아예 없으면 준비할 것이 없으므로 건너뛴다.
    next_schedule = context["next_schedule"]

    if not next_schedule or next_schedule in NEXT_SCHEDULE_SKIP_VALUES:
        return None

    # 최소 1분은 다른 콘텐츠(읽기/유튜브)에 남겨둔다
    if context["target_minutes"] - NEXT_PREP_MINUTES <= 0:
        return None

    return context["next_schedule_other_content"] or next_schedule


def pick_activity_module_slot(context, situation):
    # 회복 방식에 듣기/스트레칭/마음 정리 중 하나라도 있어야 활동 모듈(오디오가이드 등)을 고려한다
    if not any(
        content_type in YOUTUBE_CONTENT_TYPES
        for content_type in context["content_types"]
    ):
        return None

    # 최소 1분은 다른 콘텐츠(읽기/유튜브)에 남겨둔다
    remaining_minutes = context["target_minutes"] - 1

    if remaining_minutes <= 0:
        return None

    return select_activity_module(
        current_state=context["current_state"],
        situation=situation,
        remaining_minutes=remaining_minutes,
    )


def save_course_record(user, execution):
    # 실제로 사용한 시간(초)을 분 단위로 환산해 기록에 남긴다
    completed_minutes = round(execution.used_seconds / 60)

    content_types_used = ",".join(
        execution.course.contents.values_list("content_type", flat=True)
    )

    record = Record.objects.create(
        user=user,
        course=execution.course,
        category=content_types_used,
        target_minutes=execution.target_minutes,
        completed_minutes=completed_minutes,
        started_at=execution.started_at,
        completed_at=execution.ended_at,
    )

    for content in execution.course.contents.all().order_by("content_order"):
        RecordContent.objects.create(
            record=record,
            sequence=content.content_order,
            content_type=content.content_type,
            title=content.title,
            url=content.video_url or content.content_url or "",
        )

    return record


def start_course_execution(user, course):
    # execute()와 기록 재실행 API가 공유하는 실행 시작 로직

    contents = CourseContent.objects.filter(
        course=course
    ).order_by("content_order")

    if not contents.exists():
        return Response(
            {"detail": "해당 추천 코스의 콘텐츠를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND
        )

    active_execution = CourseExecution.objects.filter(
        user=user,
        status="in_progress"
    ).first()

    if active_execution:

        # 설정 시간이 이미 다 지났는데 앱에서 종료 처리를 못 받은 경우
        # (강제 종료, 네트워크 끊김 등) -> 자동으로 중단 처리하고 새 실행을 허용한다
        elapsed_seconds = (
            timezone.now() - active_execution.started_at
        ).total_seconds()

        projected_used_seconds = active_execution.used_seconds + elapsed_seconds

        if projected_used_seconds >= active_execution.target_seconds:
            active_execution.used_seconds = active_execution.target_seconds
            active_execution.ended_at = timezone.now()
            active_execution.status = "stopped"
            active_execution.save()

            record_weekly_usage(user, active_execution.used_seconds)

        else:
            return Response(
                {"detail": "현재 실행 중인 코스가 있습니다."},
                status=status.HTTP_409_CONFLICT
            )

    started_at = timezone.now()

    execution = CourseExecution.objects.create(
        user=user,
        course=course,
        target_minutes=course.total_minutes,
        started_at=started_at,
        status="in_progress",
    )

    remaining_seconds = execution.target_seconds

    execution_serializer = CourseExecutionSerializer(execution)
    contents_serializer = CourseContentSerializer(contents, many=True)

    return Response(
        {
            **execution_serializer.data,
            "guest_uuid": str(user.guest_uuid),
            "remaining_seconds": remaining_seconds,
            "contents": contents_serializer.data,
        },
        status=status.HTTP_201_CREATED
    )


class MainViewSet(viewsets.ViewSet):

    #GET /main
    def list(self,request):
        serializer = MainGETSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        time_setting = TimeSetting.objects.get(step=0)

        return Response(
            {
                "step": time_setting.step,
                "title": time_setting.title,
                "description": time_setting.description,
                "guest_uuid": user.guest_uuid,
                "target_minutes": user.target_minutes,
                "min_minutes": time_setting.min_minutes,
                "max_minutes": time_setting.max_minutes
            },
            status=status.HTTP_200_OK
        )



    #POST /main
    def create(self, request):
        serializer = MainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]
        target_minutes = serializer.validated_data["target_minutes"]

        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {
                    "detail": "사용자 정보를 찾을 수 없습니다."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user.target_minutes = target_minutes
        user.save()

        return Response(
            {
                "guest_uuid": user.guest_uuid,
                "target_minutes": user.target_minutes
            },
            status=status.HTTP_200_OK
        )



class MainQuestionViewSet(viewsets.ViewSet):

    # GET /main/questions
    def list(self, request):
        # 화면에 보여줄 순서: 장소(1) -> 다음일정(3) -> 현재상태(4) -> 회복방식(2)
        # question_id 자체(답변 저장 로직이 참조하는 값)는 그대로 두고, 노출 순서만 바꾼다.
        display_order = [1, 3, 4, 2]

        questions = list(
            Question.objects.prefetch_related("options").filter(question_id__in=display_order)
        )
        questions.sort(key=lambda q: display_order.index(q.question_id))

        serializer = QuestionSerializer(questions, many=True)

        return Response(
            {"questions": serializer.data},
            status=status.HTTP_200_OK
        )


        # POST /main/questions
    def create(self, request):
        serializer = MainAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]
        answers = serializer.validated_data["answers"]

        # 사용자 찾기
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 1번 질문 답변: 장소
        place_answer = next(
            answer for answer in answers
            if answer.get("question_id") == 1
        )

        # 2번 질문 답변: 회복 방식
        recovery_answer = next(
            answer for answer in answers
            if answer.get("question_id") == 2
        )

        # 3번 질문 답변: 다음 일정
        next_schedule_answer = next(
            answer for answer in answers
            if answer.get("question_id") == 3
        )

        # 4번 질문 답변: 현재 상태
        state_answer = next(
            answer for answer in answers
            if answer.get("question_id") == 4
        )

        # 선택지 찾기
        situation_option = Option.objects.get(
            option_id=place_answer["option_id"]
        )

        next_schedule_option = Option.objects.get(
            option_id=next_schedule_answer["option_id"]
        )

        # MainAnswer 먼저 생성
        main_answer = MainAnswer.objects.create(
            user=user,
            situation_option=situation_option,
            other_content=place_answer.get("other_content"),
            next_schedule_option=next_schedule_option,
            next_schedule_other_content=next_schedule_answer.get("other_content"),
        )

        # 2번 질문 선택지들 찾기
        preferred_options = Option.objects.filter(
            option_id__in=recovery_answer["option_ids"]
        )

        # ManyToMany 연결
        main_answer.preferred_options.set(preferred_options)

        # 4번 질문 선택지들 찾기
        current_state_options = Option.objects.filter(
            option_id__in=state_answer["option_ids"]
        )

        # ManyToMany 연결
        main_answer.current_state_options.set(current_state_options)

        return Response(
            {
                "guest_uuid": str(user.guest_uuid),
                "answers": answers,
                "message": "메인 질문 답변이 저장되었습니다."
            },
            status=status.HTTP_200_OK
        )



class CourseViewSet(viewsets.ViewSet):

    # POST /main/teumteum
    def create(self, request):

        # 1. guest_uuid 검증
        serializer = MainGETSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2-1. 틈 시간 설정 여부 확인
        if not user.target_minutes:
            return Response(
                {"detail": "틈 시간 설정이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. 사용자 추천 조건 조회
        try:
            context = get_user_context(user)
        except Exception:
            return Response(
                {"detail": "추천에 필요한 사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. 메인 질문 답변 확인
        if not context["content_types"] or not context["main_situation"]:
            return Response(
                {"detail": "메인 질문 답변을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 5. 웰니스 원문 / YouTube에서 후보 콘텐츠 가져오기
        recommended_contents = get_recommended_contents(user)

        article_contents = recommended_contents["articles"]
        youtube_contents = recommended_contents["youtube"]

        situation = context["other_content"] or context["main_situation"]
        interests = context["categories"] + context["topics"]

        # 5-1. 현재 상태에 맞는 활동 모듈(오디오가이드 등)이 있으면 한 자리 먼저 배정
        activity_module = pick_activity_module_slot(context, situation)

        # 5-2. 활동 모듈이 없을 때만, 다음 일정 준비 콘텐츠로 한 자리를 채울지 확인
        next_prep_text = None if activity_module else pick_next_prep_text(context)

        # 5-3. 전체 목표 시간 기준 추천 모듈 개수 범위 (활동 모듈/다음준비도 이 개수에 포함)
        min_module_count, max_module_count = get_module_count_range(context["target_minutes"])

        if activity_module:
            total_min = max(min_module_count - 1, 0)
            total_max = max(max_module_count - 1, 0)
            remaining_target_minutes = context["target_minutes"] - activity_module.estimated_minutes
        elif next_prep_text:
            total_min = max(min_module_count - 1, 0)
            total_max = max(max_module_count - 1, 0)
            remaining_target_minutes = context["target_minutes"] - NEXT_PREP_MINUTES
        else:
            total_min = min_module_count
            total_max = max_module_count
            remaining_target_minutes = context["target_minutes"]

        # 6. target_minutes에 가장 가까운 나머지 콘텐츠 선택
        selected_contents = select_best_contents_in_range(
            article_contents=article_contents,
            youtube_contents=youtube_contents,
            content_types=context["content_types"],
            target_minutes=remaining_target_minutes,
            min_count=total_min,
            max_count=total_max,
        )

        if selected_contents is None:
            return Response(
                {"detail": "새로운 추천 코스를 생성할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        selected_contents = allocate_content_minutes(
            selected_contents,
            remaining_target_minutes
        )

        if selected_contents is None:
            return Response(
                {"detail": "추천 코스를 생성할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 7. Course 생성
        course = Course.objects.create(
            user=user,
            title=f"{user.target_minutes}분 틈 활용법",
            description="추천이 마음에 들지 않는다면 바꿔보세요.",
            total_minutes=user.target_minutes,
            place=context["main_situation"],
            current_state=context["current_state"],
        )

        # 8. 선택된 콘텐츠 저장
        content_order = 1

        if activity_module:
            CourseContent.objects.create(
                course=course,
                content_order=content_order,
                content_type=activity_module.content_type,
                title=activity_module.title,
                description=activity_module.description or "",
                voice_script=activity_module.voice_script,
                steps=activity_module.steps,
                repeat_count=activity_module.repeat_count,
                question=activity_module.question,
                question_options=activity_module.question_options,
                allow_text_input=activity_module.allow_text_input,
                estimated_minutes=activity_module.estimated_minutes,
            )
            content_order += 1

        elif next_prep_text:
            prep = generate_next_prep_brief(
                next_schedule=next_prep_text,
                situation=situation,
                estimated_minutes=NEXT_PREP_MINUTES,
            )
            CourseContent.objects.create(
                course=course,
                content_order=content_order,
                content_type="reflection",
                title=prep["title"],
                description=prep["action_tip"] or "",
                content=prep["content"],
                voice_script=prep["content"],
                question=prep["question"],
                allow_text_input=True,
                estimated_minutes=NEXT_PREP_MINUTES,
            )
            content_order += 1

        for content in selected_contents:

            # 읽기 콘텐츠
            if "source" in content:

                if content.get("needs_generation"):
                    brief = generate_original_brief(
                        situation=situation,
                        interests=interests,
                        current_state=context["current_state"],
                        estimated_minutes=content["estimated_minutes"],
                    )
                else:
                    brief = generate_personalized_brief(
                        source_content=content.get("content") or "",
                        source_title=content["title"],
                        situation=situation,
                        interests=interests,
                        estimated_minutes=content["estimated_minutes"],
                    )

                CourseContent.objects.create(
                    course=course,
                    content_order=content_order,
                    content_type="article",
                    title=brief["title"],
                    description=brief["action_tip"] or "",
                    content=brief["content"],
                    question=brief["question"],
                    voice_script=brief["content"],
                    source=content.get("source"),
                    source_article_id=content.get("source_article_id"),
                    estimated_minutes=content["estimated_minutes"],
                )

            # YouTube 콘텐츠
            else:

                CourseContent.objects.create(
                    course=course,
                    content_order=content_order,
                    content_type="youtube",
                    title=content["title"],
                    description="",
                    video_url=content["url"],
                    thumbnail_url=content["thumbnail"],
                    channel_name=content["channel"],
                    estimated_minutes=content["estimated_minutes"],
                )

            content_order += 1

        # 9. 최종 코스 응답
        course_serializer = CourseSerializer(course)

        return Response(
            {
                "guest_uuid": str(user.guest_uuid),
                "target_minutes": user.target_minutes,
                "course": course_serializer.data,
            },
            status=status.HTTP_201_CREATED
        )


        # POST /main/teumteum/{course_id}
    def execute(self, request, course_id=None):

        # 1. guest_uuid 검증
        serializer = MainGETSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 해당 사용자의 코스 조회
        try:
            course = Course.objects.get(
                id=course_id,
                user=user
            )
        except Course.DoesNotExist:
            return Response(
                {"detail": "추천 코스를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        return start_course_execution(user, course)


    # POST /main/teumteum/execution/{execution_id}/pause
    def pause(self, request, execution_id=None):

        # 1. guest_uuid 검증
        serializer = MainGETSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 실행 기록 조회
        try:
            execution = CourseExecution.objects.get(
                id=execution_id,
                user=user
            )
        except CourseExecution.DoesNotExist:
            return Response(
                {"detail": "실행 중인 코스를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. 실행 중인지 확인
        if execution.status != "in_progress":
            return Response(
                {"detail": "현재 실행 중인 코스가 아닙니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. 이번 실행 시간 계산 (초 단위)
        now = timezone.now()

        elapsed_seconds = round(
            (now - execution.started_at).total_seconds()
        )

        # 6. 기존 사용 시간에 누적
        execution.used_seconds += elapsed_seconds

        # 7. 최대 설정 시간 초과 방지
        if execution.used_seconds > execution.target_seconds:
            execution.used_seconds = execution.target_seconds

        # 8. 일시정지 처리
        execution.status = "paused"
        execution.save()

        # 9. 남은 시간 계산 (초 단위)
        remaining_seconds = (
            execution.target_seconds - execution.used_seconds
        )

        return Response(
            {
                "execution_id": execution.id,
                "status": execution.status,
                "used_seconds": execution.used_seconds,
                "remaining_seconds": remaining_seconds,
            },
            status=status.HTTP_200_OK
        )


    # POST /main/teumteum/execution/{execution_id}/resume
    def resume(self, request, execution_id=None):

        # 1. guest_uuid 검증
        serializer = MainGETSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 실행 기록 조회
        try:
            execution = CourseExecution.objects.get(
                id=execution_id,
                user=user
            )
        except CourseExecution.DoesNotExist:
            return Response(
                {"detail": "실행 기록을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. 일시정지 상태인지 확인
        if execution.status != "paused":
            return Response(
                {"detail": "일시정지된 코스가 아닙니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. 설정한 시간을 모두 사용했는지 확인
        if execution.used_seconds >= execution.target_seconds:
            return Response(
                {"detail": "설정한 코스 시간이 모두 사용되었습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 6. 다시 타이머 시작
        execution.started_at = timezone.now()
        execution.status = "in_progress"
        execution.save()

        # 7. 남은 시간 계산 (초 단위)
        remaining_seconds = (
            execution.target_seconds - execution.used_seconds
        )

        return Response(
            {
                "execution_id": execution.id,
                "status": execution.status,
                "used_seconds": execution.used_seconds,
                "remaining_seconds": remaining_seconds,
            },
            status=status.HTTP_200_OK
        )


    def stop(self, request, execution_id=None):

        # 1. guest_uuid 검증
        serializer = MainGETSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 실행 기록 조회
        try:
            execution = CourseExecution.objects.get(
                id=execution_id,
                user=user,
                status="in_progress"
            )
        except CourseExecution.DoesNotExist:
            return Response(
                {"detail": "현재 실행 중인 코스가 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. 종료 시간과 마지막 사용 시간 계산 (초 단위)
        ended_at = timezone.now()

        elapsed_seconds = round(
            (ended_at - execution.started_at).total_seconds()
        )

        # 기존 사용 시간에 마지막 사용 시간 누적
        execution.used_seconds += elapsed_seconds

        # 최대 설정 시간 초과 방지
        if execution.used_seconds > execution.target_seconds:
            execution.used_seconds = execution.target_seconds

        # 5. 실행 정보 저장
        execution.ended_at = ended_at
        execution.status = "stopped"
        execution.save()

        # 5-1. 이번 주 누적 사용 시간에 반영
        record_weekly_usage(user, execution.used_seconds)

        # 6. 결과 반환
        return Response(
            {
                "execution_id": execution.id,
                "course_id": execution.course.id,
                "status": execution.status,
                "used_seconds": execution.used_seconds,
            },
            status=status.HTTP_200_OK
        )


    def complete(self, request, execution_id=None):

        # 1. guest_uuid 검증
        serializer = MainGETSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 실행 기록 조회
        try:
            execution = CourseExecution.objects.get(
                id=execution_id,
                user=user,
                status="in_progress"
            )
        except CourseExecution.DoesNotExist:
            return Response(
                {"detail": "현재 실행 중인 코스가 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. 마지막 실행 시간 계산 (초 단위)
        ended_at = timezone.now()

        elapsed_seconds = round(
            (ended_at - execution.started_at).total_seconds()
        )

        execution.used_seconds += elapsed_seconds

        # 아직 설정 시간이 다 안 지났으면 완료 처리 거부 (중간에 그만두려면 stop을 써야 함)
        if execution.used_seconds < execution.target_seconds:
            return Response(
                {"detail": "아직 코스 시간이 다 되지 않았습니다. 중간에 그만두려면 stop을 사용해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 최대 설정 시간 초과 방지
        if execution.used_seconds > execution.target_seconds:
            execution.used_seconds = execution.target_seconds

        # 5. 실행 완료 처리
        execution.ended_at = ended_at
        execution.status = "completed"
        execution.save()

        # 5-1. 이번 주 누적 사용 시간에 반영
        record_weekly_usage(user, execution.used_seconds)

        # 5-2. 기록(Record) 저장
        record = save_course_record(user, execution)

        # 6. 결과 반환
        return Response(
            {
                "execution_id": execution.id,
                "course_id": execution.course.id,
                "status": execution.status,
                "used_seconds": execution.used_seconds,
                "record_id": record.id,
            },
            status=status.HTTP_200_OK
        )


    # POST /main/teumteum/execution/{execution_id}/rate
    def rate(self, request, execution_id=None):

        # 1. guest_uuid, satisfaction 검증
        serializer = CourseRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]
        satisfaction = serializer.validated_data["satisfaction"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 실행 기록 조회
        try:
            execution = CourseExecution.objects.get(
                id=execution_id,
                user=user
            )
        except CourseExecution.DoesNotExist:
            return Response(
                {"detail": "실행 기록을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. 종료된 코스인지 확인
        if execution.status not in ["completed", "stopped"]:
            return Response(
                {"detail": "종료된 코스만 평가할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. 평가 저장
        execution.satisfaction = satisfaction
        execution.save()

        return Response(
            {
                "execution_id": execution.id,
                "satisfaction": execution.satisfaction,
            },
            status=status.HTTP_200_OK
        )

        # POST /main/teumteum/refresh
    def refresh(self, request):

        # 1. guest_uuid 검증
        serializer = MainGETSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 2. 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 사용자 추천 조건 조회
        try:
            context = get_user_context(user)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "추천에 필요한 사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not context["content_types"] or not context["main_situation"]:
            return Response(
                {"detail": "메인 질문 답변을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. 새로운 콘텐츠 후보 가져오기
        recommended_contents = get_recommended_contents(user)

        article_contents = recommended_contents["articles"]
        youtube_contents = recommended_contents["youtube"]

        situation = context["other_content"] or context["main_situation"]
        interests = context["categories"] + context["topics"]

        # 4-1. 현재 상태에 맞는 활동 모듈(오디오가이드 등)이 있으면 한 자리 먼저 배정
        activity_module = pick_activity_module_slot(context, situation)

        # 4-2. 활동 모듈이 없을 때만, 다음 일정 준비 콘텐츠로 한 자리를 채울지 확인
        next_prep_text = None if activity_module else pick_next_prep_text(context)

        # 4-3. 전체 목표 시간 기준 추천 모듈 개수 범위 (활동 모듈/다음준비도 이 개수에 포함)
        min_module_count, max_module_count = get_module_count_range(context["target_minutes"])

        if activity_module:
            total_min = max(min_module_count - 1, 0)
            total_max = max(max_module_count - 1, 0)
            remaining_target_minutes = context["target_minutes"] - activity_module.estimated_minutes
        elif next_prep_text:
            total_min = max(min_module_count - 1, 0)
            total_max = max(max_module_count - 1, 0)
            remaining_target_minutes = context["target_minutes"] - NEXT_PREP_MINUTES
        else:
            total_min = min_module_count
            total_max = max_module_count
            remaining_target_minutes = context["target_minutes"]

        # 5. 최종 나머지 콘텐츠 선택
        selected_contents = select_best_contents_in_range(
            article_contents=article_contents,
            youtube_contents=youtube_contents,
            content_types=context["content_types"],
            target_minutes=remaining_target_minutes,
            min_count=total_min,
            max_count=total_max,
        )

        print("===== refresh 선택 결과 =====")
        print("원문 후보 수:", len(article_contents))
        print("유튜브 후보 수:", len(youtube_contents))
        print("선호 콘텐츠 타입:", context["content_types"])
        print("목표 시간:", context["target_minutes"])
        print("selected_contents:", selected_contents)

        if selected_contents is None:
            return Response(
                {"detail": "새로운 추천 코스를 생성할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        selected_contents = allocate_content_minutes(
            selected_contents,
            remaining_target_minutes
        )

        if selected_contents is None:
            return Response(
                {"detail": "새로운 추천 코스를 생성할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 6. 새로운 Course 생성
        course = Course.objects.create(
            user=user,
            title=f"{user.target_minutes}분 틈 활용법",
            description="새로운 추천 코스입니다.",
            total_minutes=user.target_minutes,
            place=context["main_situation"],
            current_state=context["current_state"],
        )

        # 7. CourseContent 저장
        content_order = 1

        if activity_module:
            CourseContent.objects.create(
                course=course,
                content_order=content_order,
                content_type=activity_module.content_type,
                title=activity_module.title,
                description=activity_module.description or "",
                voice_script=activity_module.voice_script,
                steps=activity_module.steps,
                repeat_count=activity_module.repeat_count,
                question=activity_module.question,
                question_options=activity_module.question_options,
                allow_text_input=activity_module.allow_text_input,
                estimated_minutes=activity_module.estimated_minutes,
            )
            content_order += 1

        elif next_prep_text:
            prep = generate_next_prep_brief(
                next_schedule=next_prep_text,
                situation=situation,
                estimated_minutes=NEXT_PREP_MINUTES,
            )
            CourseContent.objects.create(
                course=course,
                content_order=content_order,
                content_type="reflection",
                title=prep["title"],
                description=prep["action_tip"] or "",
                content=prep["content"],
                voice_script=prep["content"],
                question=prep["question"],
                allow_text_input=True,
                estimated_minutes=NEXT_PREP_MINUTES,
            )
            content_order += 1

        for content in selected_contents:

            if "source" in content:

                if content.get("needs_generation"):
                    brief = generate_original_brief(
                        situation=situation,
                        interests=interests,
                        current_state=context["current_state"],
                        estimated_minutes=content["estimated_minutes"],
                    )
                else:
                    brief = generate_personalized_brief(
                        source_content=content.get("content") or "",
                        source_title=content["title"],
                        situation=situation,
                        interests=interests,
                        estimated_minutes=content["estimated_minutes"],
                    )

                CourseContent.objects.create(
                    course=course,
                    content_order=content_order,
                    content_type="article",
                    title=brief["title"],
                    description=brief["action_tip"] or "",
                    content=brief["content"],
                    question=brief["question"],
                    voice_script=brief["content"],
                    source=content.get("source"),
                    source_article_id=content.get("source_article_id"),
                    estimated_minutes=content["estimated_minutes"],
                )

            else:

                CourseContent.objects.create(
                    course=course,
                    content_order=content_order,
                    content_type="youtube",
                    title=content["title"],
                    description="",
                    video_url=content["url"],
                    thumbnail_url=content["thumbnail"],
                    channel_name=content["channel"],
                    estimated_minutes=content["estimated_minutes"],
                )

            content_order += 1

        # 8. 새로운 추천 코스 반환
        course_serializer = CourseSerializer(course)

        return Response(
            {
                "guest_uuid": str(user.guest_uuid),
                "target_minutes": user.target_minutes,
                "course": course_serializer.data,
            },
            status=status.HTTP_201_CREATED
        )