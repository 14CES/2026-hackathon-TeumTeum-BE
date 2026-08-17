
from datetime import timedelta

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import User
from teumteum.models import WeeklyUsage
from teumteum.serializers import MainGETSerializer
from teumteum.views import get_week_start

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


class WeeklyUsageViewSet(viewsets.ViewSet):

    # GET /mypage/weekly-usage?guest_uuid=
    def list(self, request):
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

        this_week_start = get_week_start(timezone.now())
        last_week_start = this_week_start - timedelta(days=7)

        this_week_usage = WeeklyUsage.objects.filter(
            user=user,
            week_start=this_week_start
        ).first()

        last_week_usage = WeeklyUsage.objects.filter(
            user=user,
            week_start=last_week_start
        ).first()

        this_week_minutes = this_week_usage.total_minutes if this_week_usage else 0
        last_week_minutes = last_week_usage.total_minutes if last_week_usage else 0

        diff_minutes = this_week_minutes - last_week_minutes

        if last_week_minutes > 0:
            diff_percent = round((diff_minutes / last_week_minutes) * 100, 1)
        else:
            diff_percent = None

        return Response(
            {
                "guest_uuid": str(user.guest_uuid),
                "this_week_start": this_week_start,
                "this_week_minutes": this_week_minutes,
                "last_week_start": last_week_start,
                "last_week_minutes": last_week_minutes,
                "diff_minutes": diff_minutes,
                "diff_percent": diff_percent,
            },
            status=status.HTTP_200_OK
        )