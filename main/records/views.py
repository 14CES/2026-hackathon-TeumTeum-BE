from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from accounts.models import User
from .models import Record
from .serializers import RecordQuerySerializer, RecordItemSerializer

class RecordListView(APIView):
    permission_classes = [AllowAny] # Query Param으로 guest_uuid 직접 검증

    def get(self, request):
        # 1. GET Query Parameter 검증
        query_serializer = RecordQuerySerializer(data=request.query_params)
        
        if not query_serializer.is_valid():
            return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        guest_uuid = query_serializer.validated_data['guest_uuid']

        # 2. 유저 존재 여부 확인 (404 Not Found 처리)
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 해당 유저의 완료 기록 조회 (최신순 정렬)
        records = Record.objects.filter(user=user).select_related('magazine').order_by('-completed_at', '-id')

        # 4. 데이터 직렬화 및 응답 (기록이 없어도 [] 빈 리스트로 200 OK)
        serializer = RecordItemSerializer(records, many=True)
        return Response({"records": serializer.data}, status=status.HTTP_200_OK)