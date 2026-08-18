from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User
from .serializers import MyPageQuerySerializer, MyPageDashboardResponseSerializer
from .utils import get_mypage_dashboard_data


class CheckMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "user_id": user.id,
            "guest_uuid": user.guest_uuid,
            "total_minutes": user.total_minutes,
            "message": "인증된 게스트 사용자입니다."
        }, status=status.HTTP_200_OK)


class MyPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. 쿼리 파라미터 유효성 검증
        query_serializer = MyPageQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        guest_uuid = query_serializer.validated_data['guest_uuid']

        # 2. 유저 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 데이터 계산
        dashboard_data = get_mypage_dashboard_data(user)

        # 4. 응답 직렬화
        response_serializer = MyPageDashboardResponseSerializer(dashboard_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


MyPageDashboardView = MyPageView

class WeeklyUsageViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        view = MyPageView.as_view()
        return view(request._request)