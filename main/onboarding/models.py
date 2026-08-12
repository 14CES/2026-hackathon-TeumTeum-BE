from django.db import models

# Create your models here.
class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    guest_uuid = models.CharField(max_length=255, unique=True)
    nickname = models.CharField(max_length=255, null=True, blank=True)
    total_minutes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'

class UserProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    status = models.JSONField(default=list)
    preferred_type = models.JSONField(default=list) 
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'