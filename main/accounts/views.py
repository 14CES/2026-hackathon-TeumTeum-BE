import uuid
from collections import Counter

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum

from .models import User
from records.models import Record

DNA_TYPES = {
    "NEWS": {
        "type": "인간 레이더",
        "description": "세상 돌아가는 일 다 꿰뚫는 정보통 DNA"
    },
    "ASMR": {
        "type": "유리멘탈 보호구역",
        "description": "작은 소음도 빗소리로 지워내는 고요 DNA"
    },
    "MUSIC": {
        "type": "방구석 디제이",
        "description": "내 삶의 BGM은 내가 직접 정하는 감성 DNA"
    },
    "MAGAZINE": {
        "type": "감성 수집가",
        "description": "자투리 시간도 화보처럼 읽어내는 매거진 DNA"
    },
    "STRETCH": {
        "type": "연체동물",
        "description": "유연함이 남다른 연체동물 DNA"
    }
}


def calculate_user_dna(user):
    records = Record.objects.filter(user=user)
    
    if records.exists():
        categories = [r.category for r in records if r.category]
        if categories:
            # 가장 많이 수행된 카테고리 추출
            most_common_cat = Counter(categories).most_common(1)[0][0]
            
            # 카테고리 키
            cat_map = {
                'NEWS': 'NEWS',
                'ASMR': 'ASMR',
                'MUSIC': 'MUSIC',
                'MAGAZINE': 'MAGAZINE',
                'BODY': 'STRETCH',
                'STRETCH': 'STRETCH',
                'MIND': 'ASMR',
                'PREPARATION': 'NEWS'
            }
            target_key = cat_map.get(most_common_cat, 'STRETCH')
            dna_info = DNA_TYPES.get(target_key, DNA_TYPES['STRETCH'])
            return dna_info

    return DNA_TYPES['STRETCH']


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
        target_uuid = request.query_params.get('user_uuid') or request.query_params.get('guest_uuid')

        # 400 Bad Request: 파라미터 누락
        if not target_uuid:
            return Response(
                {"guest_uuid": ["이 필드는 필수 항목입니다."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 400 Bad Request: UUID 형식 오류
        try:
            uuid.UUID(target_uuid)
        except ValueError:
            return Response(
                {"guest_uuid": ["유효한 UUID 형식이 아닙니다."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. 유저 조회 (404 Not Found: 미존재 사용자)
        try:
            user = User.objects.get(guest_uuid=target_uuid)
        except User.DoesNotExist:
            return Response(
                {"detail": "사용자 정보를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 누적 시간 집계 (User 모델 값 또는 records 완료 시간 합산)
        total_minutes = user.total_minutes
        if total_minutes == 0:
            agg_result = Record.objects.filter(user=user).aggregate(total=Sum('completed_minutes'))
            total_minutes = agg_result['total'] or 0

        # 4. 코스 사용 이력 기반 DNA 산출
        dna_info = calculate_user_dna(user)

        # 5. 성공 응답 (200 OK)
        response_data = {
            "nickname": user.nickname if user.nickname else "틈틈",
            "total_minutes": total_minutes,
            "dna": {
                "type": dna_info["type"],
                "description": dna_info["description"]
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)