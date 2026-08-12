
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class CheckMeView(APIView):
    # X-Guest-ID 검증 및 request.user 할당 확인
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "user_id": user.id,
            "guest_uuid": user.guest_uuid,
            "total_minutes": user.total_minutes,
            "message": "인증된 게스트 사용자입니다."
        }, status=status.HTTP_200_OK)