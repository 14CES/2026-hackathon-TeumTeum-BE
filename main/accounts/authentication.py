import uuid
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User

class GuestAuthentication(BaseAuthentication):
    def authenticate(self, request):
        guest_uuid = request.headers.get('X-Guest-ID')

        # 1. 헤더가 없는 경우: 인증 과정을 건너뜀 (None 반환)
        if not guest_uuid:
            return None

        # 2. UUID 형식 검증
        try:
            uuid.UUID(guest_uuid)
        except ValueError:
            raise AuthenticationFailed("유효하지 않은 UUID 형식입니다.")

        # 3. 유저 조회 또는 생성
        user, _ = User.objects.get_or_create(guest_uuid=guest_uuid)

        return (user, None)