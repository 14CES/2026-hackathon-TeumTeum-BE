import uuid
from rest_framework import serializers
from .models import WellnessArticle


class DiscoveryQuerySerializer(serializers.Serializer):
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


class WellnessArticleCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessArticle
        fields = [
            'id',
            'title',
            'category',
            'read_minutes',
            'image_url',
        ]


class WellnessArticleDetailSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = WellnessArticle
        fields = [
            'id',
            'title',
            'category',
            'read_minutes',
            'image_url',
            'content',
            'created_at',
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y.%m.%d") if obj.created_at else ""