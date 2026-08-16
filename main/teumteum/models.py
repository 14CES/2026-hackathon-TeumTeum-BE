from django.db import models
from accounts.models import User

class TimeSetting(models.Model):
    step = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    min_minutes = models.IntegerField()
    max_minutes = models.IntegerField()

    class Meta:
        db_table = "time_settings"

    def __str__(self):
        return self.title

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



class Course(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    total_minutes = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "courses"

    def __str__(self):
        return self.title



class CourseContent(models.Model):

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="contents")
    content_order = models.IntegerField()
    content_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    description = models.TextField()
    content = models.TextField(null=True, blank=True)

    source = models.CharField(max_length=255, null=True, blank=True)
    content_url = models.URLField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    video_url = models.URLField(null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)
    channel_name = models.CharField(max_length=255, null=True, blank=True)

    estimated_minutes = models.IntegerField()

    class Meta:
        db_table = "course_contents"

    def __str__(self):
        return self.title


class CourseExecution(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="course_executions")
    course = models.ForeignKey(Course, on_delete=models.CASCADE,related_name="executions")
    target_minutes = models.IntegerField()
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, default="in_progress")

    class Meta:
        db_table = "course_executions"

    def __str__(self):
        return f"{self.user} - {self.course}"



class WeeklyUsage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="weekly_usages"
    )
    week_start = models.DateField()
    total_minutes = models.IntegerField(default=0)

    class Meta:
        db_table = "weekly_usages"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "week_start"],
                name="unique_user_week_usage"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.week_start} - {self.total_minutes}분"