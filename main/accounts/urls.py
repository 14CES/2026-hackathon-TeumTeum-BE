from django.urls import path
from .views import MyPageDashboardView

urlpatterns = [
    path('dashboard', MyPageDashboardView.as_view(), name='mypage-dashboard'),
]