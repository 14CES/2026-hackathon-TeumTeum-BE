from django.urls import path
from .views import CheckMeView, MyPageView

urlpatterns = [
    path('check-me/', CheckMeView.as_view(), name='check_me'),
    path('', MyPageView.as_view(), name='mypage'),
]