from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from accounts.models import User
from .serializers import DiscoveryQuerySerializer
from .utils import get_discovery_data

class MagazineRecommendationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. Parameter Validation (400 Bad Request)
        serializer = DiscoveryQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        guest_uuid = serializer.validated_data['guest_uuid']

        # 2. User 존재 여부 확인 (404 Not Found)
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 발견 탭 데이터 생성 및 반환 (200 OK)
        discovery_data = get_discovery_data(user)
        return Response(discovery_data, status=status.HTTP_200_OK)