# onboarding/serializers.py
import uuid
from rest_framework import serializers
from accounts.models import User      # 👈 accounts 앱의 User 사용
from .models import UserProfile       # onboarding의 UserProfile 사용

class OnboardingSerializer(serializers.Serializer):
    guest_uuid = serializers.CharField(required=True)
    interest_category = serializers.ListField(child=serializers.CharField(), required=True)
    free_time_situation = serializers.ListField(child=serializers.CharField(), required=True)
    interest_topic = serializers.ListField(child=serializers.CharField(), required=True)

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

        # 1. accounts의 User 조회 또는 생성
        user, _ = User.objects.get_or_create(guest_uuid=guest_uuid)

        # 2. UserProfile 저장
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