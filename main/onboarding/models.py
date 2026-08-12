from django.db import models
from accounts.models import User

class UserProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    status = models.JSONField(default=list)
    preferred_type = models.JSONField(default=list) 
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'