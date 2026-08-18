import uuid
from rest_framework import serializers

class MyPageQuerySerializer(serializers.Serializer):
    guest_uuid = serializers.CharField(
        required=True, 
        error_messages={"required": "이 필드는 필수 항목입니다."}
    )

    def validate_guest_uuid(self, value):
        try:
            uuid.UUID(value)
        except ValueError:
            raise serializers.ValidationError("유효한 UUID 형식이 아닙니다.")
        return value

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