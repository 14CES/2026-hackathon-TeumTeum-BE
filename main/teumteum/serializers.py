from rest_framework import serializers

class MainGETSerializer(serializers.Serializer):
    guest_uuid = serializers.UUIDField(
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid": "유효한 UUID 형식이 아닙니다."
        }
    )


class MainSerializer(serializers.Serializer):
    guest_uuid = serializers.UUIDField(
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid": "유효한 UUID 형식이 아닙니다."
        }
    )

    target_minutes = serializers.IntegerField(
        min_value=1,
        max_value=60,
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid": "유효한 정수를 입력하세요.",
            "max_value": "분은 1분 이상 60분 이하로 설정해주세요.",
            "min_value": "분은 1분 이상 60분 이하로 설정해주세요."
        }
    )