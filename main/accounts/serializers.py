import uuid
from rest_framework import serializers

# 1. 요청 파라미터 검증용 Serializer
class MyPageQuerySerializer(serializers.Serializer):
    user_uuid = serializers.CharField(required=False)
    guest_uuid = serializers.CharField(required=False)

    def validate(self, data):
        target_uuid = data.get('user_uuid') or data.get('guest_uuid')
        
        # 1) 파라미터 누락 검증 (400 Bad Request)
        if not target_uuid:
            raise serializers.ValidationError({
                "guest_uuid": ["이 필드는 필수 항목입니다."]
            })

        # 2) UUID 형식 검증 (400 Bad Request)
        try:
            uuid.UUID(target_uuid)
        except ValueError:
            raise serializers.ValidationError({
                "guest_uuid": ["유효한 UUID 형식이 아닙니다."]
            })

        data['validated_uuid'] = target_uuid
        return data


# 2. DNA 정보 직렬화
class DnaSerializer(serializers.Serializer):
    type = serializers.CharField()
    description = serializers.CharField()


# 3. 마이페이지 최종 응답 Serializer
class MyPageResponseSerializer(serializers.Serializer):
    nickname = serializers.CharField()
    total_minutes = serializers.IntegerField()
    dna = DnaSerializer()