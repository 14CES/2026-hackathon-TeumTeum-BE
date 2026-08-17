from rest_framework import serializers
from .models import Question, Option, Course, CourseContent, CourseExecution

class MainGETSerializer(serializers.Serializer):
    guest_uuid = serializers.UUIDField(
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid": "유효한 UUID 형식이 아닙니다."
        }
    )


class CourseRatingSerializer(serializers.Serializer):
    guest_uuid = serializers.UUIDField(
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid": "유효한 UUID 형식이 아닙니다."
        }
    )

    satisfaction = serializers.ChoiceField(
        choices=["good", "neutral", "bad"],
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid_choice": "좋았어요/보통이에요/별로예요 중 하나를 선택해주세요."
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
        min_value=5,
        max_value=30,
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid": "유효한 정수를 입력하세요.",
            "max_value": "분은 5분 이상 30분 이하로 설정해주세요.",
            "min_value": "분은 5분 이상 30분 이하로 설정해주세요."
        }
    )



class MainAnswerSerializer(serializers.Serializer):
    guest_uuid = serializers.UUIDField(
            error_messages={
                "required": "이 필드는 필수 항목입니다.",
                "invalid": "유효한 UUID 형식이 아닙니다."
            }
        )
    answers = serializers.ListField(
        required=True,
        error_messages={
            "required": "이 필드는 필수 항목입니다."
        }
    )

    def validate_answers(self, value):

        def find_answer(question_id):
            return next(
                (
                    answer for answer in value
                    if answer.get("question_id") == question_id
                ),
                None
            )

        # 1번 질문: 장소 (단일 선택)
        place_answer = find_answer(1)

        if not place_answer:
            raise serializers.ValidationError(
                "지금 있는 장소를 선택해주세요."
            )

        if "option_ids" in place_answer:
            raise serializers.ValidationError(
                "장소는 하나의 선택지만 선택할 수 있습니다."
            )

        if "option_id" not in place_answer:
            raise serializers.ValidationError(
                "지금 있는 장소를 선택해주세요."
            )

        if isinstance(place_answer["option_id"], list):
            raise serializers.ValidationError(
                "장소는 하나의 선택지만 선택할 수 있습니다."
            )

        place_option_id = place_answer["option_id"]

        # 기타 선택
        if place_option_id == 5:
            if not place_answer.get("other_content"):
                raise serializers.ValidationError({
                    "other_content":
                    "'기타'를 선택한 경우 직접 작성한 내용을 입력해주세요."
                })

        # 기타가 아닌데 직접 작성한 경우
        else:
            if place_answer.get("other_content"):
                raise serializers.ValidationError({
                    "other_content":
                    "'기타' 선택 시에만 직접 작성할 수 있습니다."
                })

        # 2번 질문: 회복 방식 (다중 선택)
        recovery_answer = find_answer(2)

        if not recovery_answer:
            raise serializers.ValidationError(
                "원하는 회복 방식을 하나 이상 선택해주세요."
            )

        if "option_id" in recovery_answer:
            raise serializers.ValidationError(
                "원하는 회복 방식을 하나 이상 선택해주세요."
            )

        if not recovery_answer.get("option_ids"):
            raise serializers.ValidationError(
                "원하는 회복 방식을 하나 이상 선택해주세요."
            )

        # 3번 질문: 다음 일정 (단일 선택)
        next_schedule_answer = find_answer(3)

        if not next_schedule_answer:
            raise serializers.ValidationError(
                "다음 일정을 선택해주세요."
            )

        if "option_ids" in next_schedule_answer:
            raise serializers.ValidationError(
                "다음 일정은 하나의 선택지만 선택할 수 있습니다."
            )

        if "option_id" not in next_schedule_answer:
            raise serializers.ValidationError(
                "다음 일정을 선택해주세요."
            )

        if isinstance(next_schedule_answer["option_id"], list):
            raise serializers.ValidationError(
                "다음 일정은 하나의 선택지만 선택할 수 있습니다."
            )

        next_schedule_option_id = next_schedule_answer["option_id"]

        # 기타 선택
        if next_schedule_option_id == 15:
            if not next_schedule_answer.get("other_content"):
                raise serializers.ValidationError({
                    "other_content":
                    "'기타'를 선택한 경우 직접 작성한 내용을 입력해주세요."
                })

        # 기타가 아닌데 직접 작성한 경우
        else:
            if next_schedule_answer.get("other_content"):
                raise serializers.ValidationError({
                    "other_content":
                    "'기타' 선택 시에만 직접 작성할 수 있습니다."
                })

        # 4번 질문: 현재 상태 (다중 선택)
        state_answer = find_answer(4)

        if not state_answer:
            raise serializers.ValidationError(
                "현재 상태를 하나 이상 선택해주세요."
            )

        if "option_id" in state_answer:
            raise serializers.ValidationError(
                "현재 상태를 하나 이상 선택해주세요."
            )

        if not state_answer.get("option_ids"):
            raise serializers.ValidationError(
                "현재 상태를 하나 이상 선택해주세요."
            )

        return value


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = [
            "option_id",
            "content",
        ]


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "question_id",
            "title",
            "description",
            "options",
        ]


class CourseContentSerializer(serializers.ModelSerializer):

    class Meta:
        model = CourseContent
        fields = [
            "content_order",
            "content_type",
            "title",
            "description",
            "content",
            "source",
            "content_url",
            "image_url",
            "video_url",
            "thumbnail_url",
            "channel_name",
            "voice_script",
            "steps",
            "question",
            "question_options",
            "allow_text_input",
            "estimated_minutes",
        ]


class CourseSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source="id")
    contents = CourseContentSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            "course_id",
            "title",
            "description",
            "total_minutes",
            "contents",
        ]


class CourseExecutionSerializer(serializers.ModelSerializer):
    execution_id = serializers.IntegerField(source="id")
    course_id = serializers.IntegerField(source="course.id")
    target_seconds = serializers.IntegerField(read_only=True)

    class Meta:
        model = CourseExecution
        fields = [
            "execution_id",
            "course_id",
            "target_minutes",
            "target_seconds",
            "started_at",
            "status",
        ]