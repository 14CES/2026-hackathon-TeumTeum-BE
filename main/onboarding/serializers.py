import uuid
from rest_framework import serializers
from .models import User, UserProfile

class OnboardingSerializer(serializers.Serializer):
    guest_uuid = serializers.CharField(required=True)
    interest_category = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        error_messages={"required": "이 필드는 필수 항목입니다."}
    )
    free_time_situation = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        error_messages={"required": "이 필드는 필수 항목입니다."}
    )
    interest_topic = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        error_messages={"required": "이 필드는 필수 항목입니다."}
    )

    # UUID 형식 유효성 검사 (400 Bad Request 대응)
    def validate_guest_uuid(self, value):
        try:
            uuid.UUID(value)
        except ValueError:
            raise serializers.ValidationError("유효한 UUID 형식이 아닙니다.")
        return value

    def create(self, validated_data):
        guest_uuid = validated_data.get('guest_uuid')
        interest_category = validated_data.get('interest_category')
        free_time_situation = validated_data.get('free_time_situation')
        interest_topic = validated_data.get('interest_topic')

        user, created = User.objects.get_or_create(guest_uuid=guest_uuid)

        preferred_data = {
            "categories": interest_category,
            "topics": interest_topic
        }

        profile, _ = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'status': free_time_situation,
                'preferred_type': preferred_data,
            }
        )
        return validated_data