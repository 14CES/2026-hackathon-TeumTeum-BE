import uuid
from rest_framework import serializers

class MagazineQuerySerializer(serializers.Serializer):
    guest_uuid = serializers.UUIDField(
        required=True,
        error_messages={
            'required': '이 필드는 필수 항목입니다.',
            'invalid': '유효한 UUID 형식이 아닙니다.'
        }
    )