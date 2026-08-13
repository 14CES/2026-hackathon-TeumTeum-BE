from django.shortcuts import render

# Create your views here.
from .serializers import MainGETSerializer, MainSerializer

from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.news import get_news
from services.youtube import search_youtube

from accounts.models import User

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

        return Response(
            {
                "guest_uuid": str(user.guest_uuid),
                "target_minutes": user.target_minutes
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