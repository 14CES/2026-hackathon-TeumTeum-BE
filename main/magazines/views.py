from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from accounts.models import User
from .models import WellnessArticle
from .serializers import DiscoveryQuerySerializer, WellnessArticleDetailSerializer
from .utils import (
    get_discovery_data,
    generate_ai_recommendation_reason,
    generate_ai_summary,
)


class MagazineRecommendationView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):
        serializer = DiscoveryQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        guest_uuid = serializer.validated_data['guest_uuid']

        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        discovery_data = get_discovery_data(user)
        return Response(discovery_data, status=status.HTTP_200_OK)


class MagazineDetailView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, article_id):
        serializer = DiscoveryQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        guest_uuid = serializer.validated_data['guest_uuid']

        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            article = WellnessArticle.objects.get(id=article_id)
        except WellnessArticle.DoesNotExist:
            return Response(
                {"detail": "해당 아티클을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # OpenAI 실시간 생성
        ai_reason = generate_ai_recommendation_reason(user, article)
        ai_summary = generate_ai_summary(article)

        response_data = WellnessArticleDetailSerializer(article).data
        response_data['ai_reason'] = ai_reason
        response_data['ai_one_line_summary'] = ai_summary

        return Response(response_data, status=status.HTTP_200_OK)