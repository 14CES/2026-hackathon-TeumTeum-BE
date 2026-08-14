from django.db import models
from accounts.models import User

class Magazine(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    duration_minutes = models.IntegerField()
    content = models.TextField()
    audio_url = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'magazines'

class Record(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records')
    magazine = models.ForeignKey(Magazine, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=255)
    target_minutes = models.IntegerField()
    completed_minutes = models.IntegerField()
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'records'

class RecordContent(models.Model):
    id = models.BigAutoField(primary_key=True)
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='contents')
    sequence = models.IntegerField()  # order(순서)로 매핑될 필드
    content_type = models.CharField(max_length=50)  # 'youtube', 'magazine' 등
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=255)  # content_url로 매핑될 필드

    class Meta:
        db_table = 'record_contents'
        ordering = ['sequence']