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
    situation_option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="situation_answers", null=True)    # 1번 질문: 장소
    other_content = models.TextField(null=True, blank=True)                                                     # 장소 '기타' 선택 시 직접 입력
    preferred_options = models.ManyToManyField(Option, related_name="preferred_answers")                        # 2번 질문: 회복 방식 (여러 개)
    next_schedule_option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="next_schedule_answers", null=True)   # 3번 질문: 다음 일정
    next_schedule_other_content = models.TextField(null=True, blank=True)                                       # 다음 일정 '기타' 선택 시 직접 입력
    current_state_options = models.ManyToManyField(Option, related_name="current_state_answers")                    # 4번 질문: 현재 상태 (여러 개)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_answers"



class Course(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    total_minutes = models.IntegerField()
    place = models.CharField(max_length=50, null=True, blank=True)         # 생성 당시 장소 (마이페이지 패턴 분석용)
    current_state = models.JSONField(default=list, blank=True)             # 생성 당시 현재 상태 (마이페이지 패턴 분석용)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "courses"

    def __str__(self):
        return self.title



class YoutubeVideoSource(models.Model):
    # 유튜브 실시간 검색이 부족할 때 쓰는 더미 풀. "스트레칭/케어" 계열 영상을 미리 채워둔다.
    video_id = models.CharField(max_length=32, unique=True)
    url = models.URLField()
    title = models.CharField(max_length=255)
    channel_name = models.CharField(max_length=255, null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)
    estimated_minutes = models.IntegerField()
    tags = models.JSONField(default=list)   # 회복방식과 매칭 (예: "스트레칭")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "youtube_video_sources"

    def __str__(self):
        return self.title


class WellnessArticleSource(models.Model):
    # 팀이 직접 쓴 웰니스 원문 풀. "읽기" 콘텐츠는 뉴스 API 대신 여기서 골라 AI가 재구성한다.
    title = models.CharField(max_length=255)
    content = models.TextField()
    source = models.CharField(max_length=255, default="틈틈 자체 작성")  # 원문 출처 (매체명/URL, 자체 작성이면 "틈틈 자체 작성")
    topics = models.JSONField(default=list)   # 관심 웰니스 옵션과 매칭 (예: "피부", "몸", "마음", "수면")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wellness_article_sources"

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
    source_article = models.ForeignKey(WellnessArticleSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="course_contents")
    content_url = models.URLField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    video_url = models.URLField(null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)
    channel_name = models.CharField(max_length=255, null=True, blank=True)

    voice_script = models.TextField(null=True, blank=True)                     # TTS로 읽어줄 텍스트 (article 선택, audio_guide 추천)
    steps = models.JSONField(null=True, blank=True, default=list)              # 단계별 동작/호흡 타이밍 (stretch_guide, audio_guide)
    repeat_count = models.IntegerField(default=1)                              # steps 세트를 몇 번 반복해야 estimated_minutes를 채우는지 (stretch_guide, audio_guide)
    question = models.CharField(max_length=255, null=True, blank=True)         # 질문 (reflection, skin_check)
    question_options = models.JSONField(null=True, blank=True, default=list)   # 질문 선택지 (reflection, skin_check)
    allow_text_input = models.BooleanField(default=False)                      # 자유 입력 허용 여부 (reflection)

    estimated_minutes = models.IntegerField()

    class Meta:
        db_table = "course_contents"

    def __str__(self):
        return self.title


class CourseExecution(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="course_executions")
    course = models.ForeignKey(Course, on_delete=models.CASCADE,related_name="executions")
    target_minutes = models.IntegerField()             # 최초 설정값 (분 단위)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    used_seconds = models.IntegerField(default=0)      # 실행 중 누적 사용 시간 (초 단위)
    status = models.CharField(max_length=30, default="in_progress")
    satisfaction = models.CharField(max_length=20, null=True, blank=True)  # good, neutral, bad

    class Meta:
        db_table = "course_executions"

    @property
    def target_seconds(self):
        return self.target_minutes * 60

    def __str__(self):
        return f"{self.user} - {self.course}"


class ActivityModuleTemplate(models.Model):
    # 호흡/스트레칭/마음정리/피부체크처럼 검색 없이 재사용하는 웰니스 활동 모듈 카탈로그
    content_type = models.CharField(max_length=50)   # audio_guide, stretch_guide, reflection, skin_check
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    voice_script = models.TextField(null=True, blank=True)
    steps = models.JSONField(null=True, blank=True, default=list)
    repeat_count = models.IntegerField(default=1)       # steps 세트를 몇 번 반복해야 estimated_minutes를 채우는지
    question = models.CharField(max_length=255, null=True, blank=True)
    question_options = models.JSONField(null=True, blank=True, default=list)
    allow_text_input = models.BooleanField(default=False)

    estimated_minutes = models.IntegerField()
    tags = models.JSONField(default=list)               # 현재 상태 옵션 텍스트와 매칭 (예: "피곤해요")
    allowed_contexts = models.JSONField(default=list)    # 장소 옵션 텍스트와 매칭 (예: "이동 중"), 비어있으면 장소 무관
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "activity_module_templates"

    def __str__(self):
        return self.title


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