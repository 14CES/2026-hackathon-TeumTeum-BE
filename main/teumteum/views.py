from django.shortcuts import render

# Create your views here.
from .serializers import (
    MainGETSerializer,
    MainSerializer,
    MainAnswerSerializer,
    QuestionSerializer,
    CourseSerializer,
)

from .models import (
    TimeSetting,
    Question,
    Option,
    MainAnswer,
    Course,
    CourseContent,
)

from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.news import get_news
from services.youtube import search_youtube

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



