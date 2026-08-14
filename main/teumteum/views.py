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
)

from .models import (
    TimeSetting,
    Question,
    Option,
    MainAnswer,
    Course,
    CourseContent,
    CourseExecution,
)

from rest_framework import viewsets, status
from rest_framework.response import Response

from services.news import get_news
from services.youtube import search_youtube
from services.openai_service import (get_user_context, get_recommended_contents)
from services.course import select_best_contents

from accounts.models import User
from onboarding.models import UserProfile

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
        questions = Question.objects.prefetch_related("options").order_by("question_id")

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

        # 1번 질문 답변
        first_answer = next(
            answer for answer in answers
            if answer.get("question_id") == 1
        )

        # 2번 질문 답변
        second_answer = next(
            answer for answer in answers
            if answer.get("question_id") == 2
        )

        # 1번 질문 선택지 찾기
        situation_option = Option.objects.get(
            option_id=first_answer["option_id"]
        )

        # MainAnswer 먼저 생성
        main_answer = MainAnswer.objects.create(
            user=user,
            situation_option=situation_option,
            other_content=first_answer.get("other_content")
        )

        # 2번 질문 선택지들 찾기
        preferred_options = Option.objects.filter(
            option_id__in=second_answer["option_ids"]
        )

        # ManyToMany 연결
        main_answer.preferred_options.set(preferred_options)

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

        # 5. NewsData / YouTube에서 후보 콘텐츠 가져오기
        recommended_contents = get_recommended_contents(user)

        news_contents = recommended_contents["news"]
        youtube_contents = recommended_contents["youtube"]

        # 6. target_minutes에 가장 가까운 콘텐츠 3개 선택
        selected_contents = select_best_contents(
            news_contents=news_contents,
            youtube_contents=youtube_contents,
            content_types=context["content_types"],
            target_minutes=context["target_minutes"],
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
        )

        # 8. 선택된 콘텐츠 저장
        for index, content in enumerate(selected_contents, start=1):

            # 읽기 콘텐츠
            if "source" in content:

                CourseContent.objects.create(
                    course=course,
                    content_order=index,
                    content_type="article",
                    title=content["title"],
                    description=content.get("description") or "",
                    source=content.get("source"),
                    content_url=content.get("url"),
                    image_url=content.get("image_url"),
                    estimated_minutes=content["estimated_minutes"],
                )

            # YouTube 콘텐츠
            else:

                CourseContent.objects.create(
                    course=course,
                    content_order=index,
                    content_type="youtube",
                    title=content["title"],
                    description="",
                    video_url=content["url"],
                    thumbnail_url=content["thumbnail"],
                    channel_name=content["channel"],
                    estimated_minutes=content["estimated_minutes"],
                )

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

        # 4. 코스 콘텐츠 조회
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
            return Response(
                {"detail": "현재 실행 중인 코스가 있습니다."},
                status=status.HTTP_409_CONFLICT
            )

        # 5. 코스 실행 기록 생성
        started_at = timezone.now()

        execution = CourseExecution.objects.create(
            user=user,
            course=course,
            target_minutes=course.total_minutes,
            started_at=started_at,
            status="in_progress",
        )

        # 6. 실행 시작 시점의 남은 시간
        remaining_seconds = course.total_minutes * 60

        # 7. Serializer
        execution_serializer = CourseExecutionSerializer(execution)

        contents_serializer = CourseContentSerializer(
            contents,
            many=True
        )

        # 8. 응답
        return Response(
            {
                **execution_serializer.data,
                "guest_uuid": str(user.guest_uuid),
                "remaining_seconds": remaining_seconds,
                "contents": contents_serializer.data,
            },
            status=status.HTTP_201_CREATED
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

        # 4. 기존 추천 콘텐츠 URL 수집
        used_content_urls = set(
            CourseContent.objects
            .filter(course__user=user)
            .exclude(content_url__isnull=True)
            .exclude(content_url="")
            .values_list("content_url", flat=True)
        )

        used_video_urls = set(
            CourseContent.objects
            .filter(course__user=user)
            .exclude(video_url__isnull=True)
            .exclude(video_url="")
            .values_list("video_url", flat=True)
        )

        # 5. 새로운 콘텐츠 후보 가져오기
        recommended_contents = get_recommended_contents(user)

        news_contents = [
            content
            for content in recommended_contents["news"]
            if content.get("url") not in used_content_urls
        ]

        youtube_contents = [
            content
            for content in recommended_contents["youtube"]
            if content.get("url") not in used_video_urls
        ]

        # 6. 최종 콘텐츠 3개 선택
        selected_contents = select_best_contents(
            news_contents=news_contents,
            youtube_contents=youtube_contents,
            content_types=context["content_types"],
            target_minutes=context["target_minutes"],
        )

        if selected_contents is None:
            return Response(
                {"detail": "새로운 추천 코스를 생성할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 7. 새로운 Course 생성
        course = Course.objects.create(
            user=user,
            title=f"{user.target_minutes}분 틈 활용법",
            description="새로운 추천 코스입니다.",
            total_minutes=user.target_minutes,
        )

        # 8. CourseContent 저장
        for index, content in enumerate(selected_contents, start=1):

            if "source" in content:

                CourseContent.objects.create(
                    course=course,
                    content_order=index,
                    content_type="article",
                    title=content["title"],
                    description=content.get("description") or "",
                    source=content.get("source"),
                    content_url=content.get("url"),
                    image_url=content.get("image_url"),
                    estimated_minutes=content["estimated_minutes"],
                )

            else:

                CourseContent.objects.create(
                    course=course,
                    content_order=index,
                    content_type="youtube",
                    title=content["title"],
                    description="",
                    video_url=content["url"],
                    thumbnail_url=content["thumbnail"],
                    channel_name=content["channel"],
                    estimated_minutes=content["estimated_minutes"],
                )

        # 9. 새로운 추천 코스 반환
        course_serializer = CourseSerializer(course)

        return Response(
            {
                "guest_uuid": str(user.guest_uuid),
                "target_minutes": user.target_minutes,
                "course": course_serializer.data,
            },
            status=status.HTTP_201_CREATED
        )