import uuid
from rest_framework import serializers
from accounts.models import User
from .models import Record

# 1. 사용자 코스 기록 전체 조회용 Serializer
class RecordItemSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source='id')
    date = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    total_minutes = serializers.IntegerField(source='completed_minutes')

    class Meta:
        model = Record
        fields = ['record_id', 'date', 'title', 'total_minutes']

    def get_date(self, obj):
        target_date = obj.completed_at if obj.completed_at else obj.started_at
        return target_date.strftime('%Y-%m-%d') if target_date else None

    def get_title(self, obj):
        first_content = next(iter(obj.contents.all()), None)
        if first_content:
            return first_content.title

        if obj.magazine and obj.magazine.title:
            return obj.magazine.title

        return f"{obj.category} 코스 완료" if obj.category else "코스 완료"


# 2. guest_uuid 검증 공통 Serializer
class RecordQuerySerializer(serializers.Serializer):
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