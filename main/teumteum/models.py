from django.db import models
from accounts.models import User


class Question(models.Model):
    question_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)

    class Meta:
        db_table = "questions"

    def __str__(self):
        return self.title


class Option(models.Model):

    option_id = models.IntegerField(unique=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    content = models.CharField(max_length=255)

    class Meta:
        db_table = "options"

    def __str__(self):
        return self.content


class MainAnswer(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="main_answers")
    situation_option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="situation_answers", null=True)    # 1번 질문에서 선택한 선택지 하나
    other_content = models.TextField(null=True, blank=True)                                                     # '기타' 선택 시 직접 입력
    preferred_options = models.ManyToManyField(Option, related_name="preferred_answers")                        # 2번 질문에서 선택한 선택지 여러 개
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_answers"