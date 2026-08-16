import uuid
from rest_framework import serializers
from accounts.models import User
from .models import Record, RecordContent

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
        if obj.magazine and obj.magazine.title:
            return obj.magazine.title
        
        category_titles = {
            'MIND': '도파민 스크롤을 끊어내고 뇌에 선물한 사운드',
            'BODY': '움츠러들었던 목과 어깨를 펴준 5분의 기적',
            'PREPARATION': '다음 약속을 위해 정비한 나만의 마인드셋'
        }
        return category_titles.get(obj.category, f"{obj.category} 코스 완료")


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


# 3. 코스 재진입
class CourseContentSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(source='sequence') # 실제 DB 필드명에 맞춰 sequence/order 수정
    content_type = serializers.CharField()
    title = serializers.CharField()
    content_url = serializers.CharField(source='url')   # 실제 DB 필드명에 맞춰 url/content_url 수정

    class Meta:
        model = RecordContent
        fields = ['order', 'content_type', 'title', 'content_url']


# 3-2. 재진입 API 최종 응답 Structure
class RecordReentryResponseSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source='id')
    title = serializers.SerializerMethodField()
    total_minutes = serializers.IntegerField(source='target_minutes')
    contents = serializers.SerializerMethodField()

    class Meta:
        model = Record
        fields = ['record_id', 'title', 'total_minutes', 'contents']

    def get_title(self, obj):
        if hasattr(obj, 'magazine') and obj.magazine and obj.magazine.title:
            return obj.magazine.title
        
        category_titles = {
            'MIND': '도파민 스크롤을 끊어내고 뇌에 선물한 사운드',
            'BODY': '움츠러들었던 목과 어깨를 펴준 5분의 기적',
            'PREPARATION': '다음 약속을 위해 정비한 나만의 마인드셋'
        }
        return category_titles.get(obj.category, f"{obj.category} 코스")

    def get_contents(self, obj):
        contents = obj.contents.all().order_by('sequence')
        return CourseContentSerializer(contents, many=True).data


class RecordSaveSerializer(serializers.Serializer):
    guest_uuid = serializers.CharField(
        required=True,
        error_messages={
            "required": "이 필드는 필수 항목입니다."
        }
    )

    def validate_guest_uuid(self, value):
        try:
            uuid.UUID(value)
        except ValueError:
            raise serializers.ValidationError(
                "유효한 UUID 형식이 아닙니다."
            )

        return value