import uuid
from rest_framework import serializers
from accounts.models import User
from .models import UserProfile

# 실제 UI 기반 질문별 option_id 매핑 테이블
ONBOARDING_DATA = {
    1: [1, 2, 3],       # 마음-틈, 몸-틈, 준비-틈
    2: [4, 5, 6, 7],    # 이동할 때, 약속 전에, 휴식할 때, 업무 및 공부 중에
    3: [8, 9, 10, 11]   # 트렌드·이슈, 멘탈 케어, 건강, 휴식
}

ALL_OPTION_IDS = {opt for opts in ONBOARDING_DATA.values() for opt in opts}

class SingleAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(required=True)
    option_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )

class OnboardingAnswerSerializer(serializers.Serializer):
    guest_uuid = serializers.CharField(
        required=True,
        error_messages={"required": "이 필드는 필수 항목입니다."}
    )
    answers = serializers.ListField(
        child=SingleAnswerSerializer(),
        required=True,
        error_messages={"required": "이 필드는 필수 항목입니다."}
    )

    def validate_guest_uuid(self, value):
        try:
            uuid.UUID(value)
        except ValueError:
            raise serializers.ValidationError("유효한 UUID 형식이 아닙니다.")
        return value

    def validate_answers(self, answers):
        if not answers:
            raise serializers.ValidationError("이 필드는 필수 항목입니다.")

        for ans in answers:
            q_id = ans.get('question_id')
            opt_ids = ans.get('option_ids', [])

            # 존재하지 않는 질문 ID 검증
            if q_id not in ONBOARDING_DATA:
                raise serializers.ValidationError("존재하지 않는 질문입니다.")

            # 존재하지 않는 선택지 및 불일치 검증
            for opt_id in opt_ids:
                if opt_id not in ALL_OPTION_IDS:
                    raise serializers.ValidationError("존재하지 않는 선택지입니다.")
                if opt_id not in ONBOARDING_DATA[q_id]:
                    raise serializers.ValidationError("해당 질문에 속하지 않는 선택지입니다.")

        return answers

    def create(self, validated_data):
        guest_uuid = validated_data.get('guest_uuid')
        answers = validated_data.get('answers')

        user, _ = User.objects.get_or_create(guest_uuid=guest_uuid)

        # 답변 데이터 정돈 후 DB 저장 (user_profiles의 status, preferred_type에 매핑)
        answers_dict = {ans['question_id']: ans['option_ids'] for ans in answers}

        # 질문 2: 상황(status) / 질문 1 & 3: 카테고리 및 관심사(preferred_type)
        status_data = answers_dict.get(2, [])
        preferred_data = {
            "categories": answers_dict.get(1, []),
            "topics": answers_dict.get(3, [])
        }

        profile, _ = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'status': status_data,
                'preferred_type': preferred_data,
            }
        )
        return validated_data