from django.db import models
from accounts.models import User

class WellnessArticle(models.Model):
    # 1. 화면 표시용 카테고리
    CATEGORY_CHOICES = [
        ('스트레칭', '스트레칭'),
        ('건강', '건강'),
        ('마음', '마음'),
        ('영양', '영양'),
        ('피부', '피부'),
        ('수면', '수면'),
    ]

    # 2. 온보딩 / 틈 입력 연계 선택지 (복수 선택)
    CONTENT_TYPE_CHOICES = [
        ('독서', '독서'),
        ('듣기', '듣기'),
        ('스트레칭', '스트레칭'),
        ('마인드컨트롤', '마인드컨트롤'),
    ]

    title = models.CharField(max_length=200, help_text="아티클 제목")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, help_text="표시 카테고리")
    read_minutes = models.PositiveIntegerField(default=1, help_text="예상 소요 시간 (n분 읽기)")
    image_url = models.URLField(max_length=500, blank=True, null=True, help_text="썸네일/상세 이미지 URL")
    content = models.TextField(help_text="아티클/뉴스 본문 내용")
    
    # AI 틈틈 한 줄 정리
    ai_summary = models.TextField(
        blank=True, 
        null=True, 
        help_text="AI 틈틈 한 줄 정리 (상세 화면 하단)"
    )

    # 1) 온보딩 연계 매칭 태그
    target_wellness = models.JSONField(
        default=list, 
        blank=True, 
        help_text="온보딩 관심 웰니스 매칭 e.g., ['피부', '몸', '마음', '수면']"
    )
    target_content_types = models.JSONField(
        default=list, 
        blank=True, 
        help_text="온보딩 관심 콘텐츠/회복방식 매칭 e.g., ['독서', '듣기', '스트레칭', '마인드컨트롤']"
    )

    # 2) 홈화면 연계 매칭 태그 (기록 기반)
    target_states = models.JSONField(
        default=list, 
        blank=True, 
        help_text="현재 상태 매칭 e.g., ['피곤해요', '긴장돼요', '복잡해요', '몸이 뻐근해요', '피부가 신경 쓰여요']"
    )
    target_places = models.JSONField(
        default=list, 
        blank=True, 
        help_text="현재 장소/틈 매칭 e.g., ['이동 중', '카페·실내', '학교·회사', '집', '약속 전', '휴식 중']"
    )
    target_schedules = models.JSONField(
        default=list, 
        blank=True, 
        help_text="다음 일정 매칭 e.g., ['수업·회의', '친구·약속', '업무·과제', '귀가·휴식']"
    )

    created_at = models.DateField(auto_now_add=True, help_text="등록일자")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wellness_articles'
        verbose_name = '웰니스 아티클'
        verbose_name_plural = '웰니스 아티클 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category}] {self.title}"


class ArticleBookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarked_articles')
    article = models.ForeignKey(WellnessArticle, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'article_bookmarks'
        unique_together = ('user', 'article')
        verbose_name = '아티클 북마크'
        verbose_name_plural = '아티클 북마크 목록'

    def __str__(self):
        return f"{self.user.guest_uuid} - {self.article.title}"