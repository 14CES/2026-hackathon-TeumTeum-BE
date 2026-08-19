import uuid
from rest_framework import serializers

class MyPageQuerySerializer(serializers.Serializer):
    guest_uuid = serializers.CharField(required=False)
    user_uuid = serializers.CharField(required=False)

    def validate(self, data):
        target_uuid = data.get('guest_uuid') or data.get('user_uuid')

        # 1. 파라미터 누락 검증 (400 Bad Request)
        if not target_uuid:
            raise serializers.ValidationError({
                "guest_uuid": ["이 필드는 필수 항목입니다."]
            })

        # 2. UUID 형식 유효성 검증 (400 Bad Request)
        try:
            uuid.UUID(target_uuid)
        except ValueError:
            raise serializers.ValidationError({
                "guest_uuid": ["유효한 UUID 형식이 아닙니다."]
            })

        data['guest_uuid'] = target_uuid
        return data


# 2. 마이페이지 대시보드 응답용 Serializer
class WeeklyRecoverySerializer(serializers.Serializer):
    current_week_minutes = serializers.IntegerField()
    previous_week_minutes = serializers.IntegerField()
    diff_minutes = serializers.IntegerField()
    growth_rate = serializers.IntegerField()
    executed_courses = serializers.IntegerField()
    completion_rate = serializers.IntegerField()


class AIDiscoverySerializer(serializers.Serializer):
    summary_text = serializers.CharField()


class TeumPatternSerializer(serializers.Serializer):
    most_frequent_place = serializers.CharField()
    most_frequent_state = serializers.CharField()
    best_activity = serializers.CharField()
    avg_duration_minutes = serializers.IntegerField()


class NextSuggestionPresetSerializer(serializers.Serializer):
    target_minutes = serializers.IntegerField()
    place = serializers.CharField()
    recovery_method = serializers.CharField()
    course_name = serializers.CharField()


class NextSuggestionSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    preset = NextSuggestionPresetSerializer()


class MyPageDashboardResponseSerializer(serializers.Serializer):
    weekly_recovery = WeeklyRecoverySerializer()
    ai_discovery = AIDiscoverySerializer()
    teum_pattern = TeumPatternSerializer()
    next_suggestion = NextSuggestionSerializer()