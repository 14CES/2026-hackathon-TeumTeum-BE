from django.urls import path
from .views import CheckMeView

urlpatterns = [
    path('check-me/', CheckMeView.as_view(), name='check_me'),
]