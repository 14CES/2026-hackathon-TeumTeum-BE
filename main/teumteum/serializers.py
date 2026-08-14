from rest_framework import serializers
from .models import Question, Option, Course, CourseContent, CourseExecution

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
        min_value=3,
        max_value=60,
        error_messages={
            "required": "이 필드는 필수 항목입니다.",
            "invalid": "유효한 정수를 입력하세요.",
            "max_value": "분은 3분 이상 60분 이하로 설정해주세요.",
            "min_value": "분은 3분 이상 60분 이하로 설정해주세요."
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

        # 1번 질문 답변 찾기
        first_answer = next(
            (
                answer for answer in value
                if answer.get("question_id") == 1
            ),
            None
        )

        # 첫 번째 질문 답변 누락
        if not first_answer:
            raise serializers.ValidationError(
                "현재 당신의 상황에 대한 답변을 선택해주세요."
            )

        # 첫 번째 질문에서 option_ids 사용
        if "option_ids" in first_answer:
            raise serializers.ValidationError(
                "첫 번째 질문은 하나의 선택지만 선택할 수 있습니다."
            )

        # option_id 누락
        if "option_id" not in first_answer:
            raise serializers.ValidationError(
                "현재 당신의 상황에 대한 답변을 선택해주세요."
            )

        # option_id에 리스트를 넣은 경우
        if isinstance(first_answer["option_id"], list):
            raise serializers.ValidationError(
                "첫 번째 질문은 하나의 선택지만 선택할 수 있습니다."
            )

        # 첫 번째 질문 선택값
        option_id = first_answer["option_id"]

        # 기타 선택
        if option_id == 4:
            if not first_answer.get("other_content"):
                raise serializers.ValidationError({
                    "other_content":
                    "'기타'를 선택한 경우 직접 작성한 내용을 입력해주세요."
                })

        # 기타가 아닌데 직접 작성한 경우
        else:
            if first_answer.get("other_content"):
                raise serializers.ValidationError({
                    "other_content":
                    "'기타' 선택 시에만 직접 작성할 수 있습니다."
                })



        # 2번 질문 답변 찾기
        second_answer = next(
            (
                answer for answer in value
                if answer.get("question_id") == 2
            ),
            None
        )

        # 두 번째 질문 답변 누락
        if not second_answer:
            raise serializers.ValidationError(
                "원하는 콘텐츠를 하나 이상 선택해주세요."
            )

        # 두 번째 질문에서 option_id 사용
        if "option_id" in second_answer:
            raise serializers.ValidationError(
                "원하는 콘텐츠를 하나 이상 선택해주세요."
            )

        # option_ids 누락 또는 빈 배열
        if not second_answer.get("option_ids"):
            raise serializers.ValidationError(
                "원하는 콘텐츠를 하나 이상 선택해주세요."
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

    class Meta:
        model = CourseExecution
        fields = [
            "execution_id",
            "course_id",
            "target_minutes",
            "started_at",
            "status",
        ]