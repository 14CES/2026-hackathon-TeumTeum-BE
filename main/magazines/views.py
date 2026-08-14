from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.models import User
from .serializers import MagazineQuerySerializer
from .utils import fetch_recommended_news

class MagazineRecommendationView(APIView):
    def get(self, request):
        # 1. Parameter Validation (400 Bad Request)
        serializer = MagazineQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        guest_uuid = serializer.validated_data['guest_uuid']

        # 2. User 존재 여부 확인 (404 Not Found - 사용자 정보 없음)
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. UserProfile 모델
        user_interest = None
        if hasattr(user, 'profile') and user.profile.preferred_type:
            preferred = user.profile.preferred_type
            if isinstance(preferred, list) and len(preferred) > 0:
                user_interest = preferred[0]
            elif isinstance(preferred, str):
                user_interest = preferred

        # 4. 추천 매거진 데이터 가져오기 (외부 NewsData API 또는 Fallback)
        news_data = fetch_recommended_news(user_interest=user_interest)

        # 5. 성공 응답 반환 (200 OK)
        response_data = {
            "id": 1,
            "title": news_data["title"],
            "content_type": news_data["content_type"],
            "read_minutes": news_data["read_minutes"],
            "content": news_data["content"],
            "content_url": news_data["content_url"]
        }

        return Response(response_data, status=status.HTTP_200_OK)