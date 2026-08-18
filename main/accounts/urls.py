from django.urls import path
from .views import CheckMeView, MyPageView

urlpatterns = [
    path('me', CheckMeView.as_view(), name='check-me'),
]