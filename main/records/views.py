from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from accounts.models import User
from teumteum.models import CourseExecution
from .models import Record, RecordContent
from .serializers import (
    RecordQuerySerializer, 
    RecordItemSerializer,
    RecordReentryResponseSerializer,
    RecordSaveSerializer
)
from django.utils import timezone

# 1. 기록 목록 조회 API
class RecordListView(APIView):
    permission_classes = [AllowAny] # Query Param으로 guest_uuid 직접 검증

    def get(self, request):
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


    def post(self, request):
        serializer = RecordSaveSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        guest_uuid = serializer.validated_data["guest_uuid"]

        # 사용자 조회
        try:
            user = User.objects.get(guest_uuid=guest_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 현재 실행 중인 코스 조회
        execution = (
            CourseExecution.objects
            .filter(
                user=user,
                status="in_progress"
            )
            .order_by("-started_at")
            .first()
        )

        if not execution:
            return Response(
                {"detail": "실행 중인 코스를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 완료 시간
        completed_at = timezone.now()

        completed_minutes = execution.target_minutes

        # 카테고리 설정
        category = "MIND"

        record = Record.objects.create(
            user=user,
            category=category,
            target_minutes=execution.target_minutes,
            completed_minutes=completed_minutes,
            started_at=execution.started_at,
            completed_at=completed_at,
        )

        # 실행한 코스의 콘텐츠를 기록 콘텐츠로 복사
        for content in execution.course.contents.all().order_by("content_order"):
            if content.content_type == "youtube":
                url = content.video_url
                content_type = "youtube"
            else:
                url = content.content_url
                content_type = "article"

            RecordContent.objects.create(
                record=record,
                sequence=content.content_order,
                content_type=content_type,
                title=content.title,
                url=url or "",
            )

        # 실행 상태 완료 처리
        execution.status = "completed"
        execution.save(update_fields=["status"])

        return Response(
            {
                "record_id": record.id,
                "completed_minutes": record.completed_minutes,
                "completed_at": record.completed_at,
            },
            status=status.HTTP_201_CREATED
        )


# 2. 코스 재진입(다시 쉬어가기) API
class RecordReentryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, record_id):
        # 1. Request Body 검증 (400 Bad Request: guest_uuid 누락/형식 오류)
        body_serializer = RecordQuerySerializer(data=request.data)
        if not body_serializer.is_valid():
            return Response(body_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        guest_uuid = body_serializer.validated_data['guest_uuid']

        # 2. 기록 존재 여부 확인 (404 Not Found: 존재하지 않는 record_id)
        try:
            record = Record.objects.prefetch_related('contents').get(id=record_id)
        except Record.DoesNotExist:
            return Response(
                {"detail": "존재하지 않는 기록입니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 접근 권한 확인 (403 Forbidden: 다른 사용자의 기록 접근 시도)
        if str(record.user.guest_uuid) != str(guest_uuid):
            return Response(
                {"detail": "해당 기록에 접근할 권한이 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 4. 성공 응답 반환 (200 OK)
        response_serializer = RecordReentryResponseSerializer(record)
        return Response(response_serializer.data, status=status.HTTP_200_OK)