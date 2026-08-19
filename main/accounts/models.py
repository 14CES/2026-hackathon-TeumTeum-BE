# accounts/models.py
from django.db import models

class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    guest_uuid = models.CharField(max_length=255, unique=True)
    nickname = models.CharField(max_length=255, null=True, blank=True)
    total_minutes = models.IntegerField(default=0)
    target_minutes = models.IntegerField(default=5)  # 최소 허용값(5분)과 맞춰서, 처음 화면에 5분으로 뜨게 함
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return f"User({self.id}) - {self.guest_uuid}"
