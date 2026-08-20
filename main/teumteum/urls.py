from django.urls import path, include
from . import views
from .views import *
from rest_framework import routers

from django.conf import settings
from django.conf.urls.static import static

from accounts.views import WeeklyUsageViewSet

app_name = "teumteum"

default_router = routers.SimpleRouter(trailing_slash=False)

default_router.register("main", MainViewSet, basename="main")
default_router.register("main/questions", MainQuestionViewSet, basename="questions")
default_router.register("main/teumteum", CourseViewSet, basename="course")
default_router.register("mypage/weekly-usage", WeeklyUsageViewSet, basename="weekly-usage")

urlpatterns = [
    path("main/teumteum/<int:course_id>", CourseViewSet.as_view({"post": "execute"}), name="course-execute"),
    path("main/teumteum/refresh", CourseViewSet.as_view({"post": "refresh"}), name="course-refresh"),
    path("", include(default_router.urls)),
    path("main/teumteum/<int:execution_id>/pause", CourseViewSet.as_view({"post": "pause"}), name="course-pause"),
    path("main/teumteum/<int:execution_id>/resume", CourseViewSet.as_view({"post": "resume"}), name="course-resume"),
    path("main/teumteum/<int:execution_id>/skip", CourseViewSet.as_view({"post": "skip"}), name="course-skip"),
    path("main/teumteum/<int:execution_id>/stop", CourseViewSet.as_view({"post": "stop"})),
    path("main/teumteum/<int:execution_id>/complete", CourseViewSet.as_view({"post": "complete"}), name="course-complete"),
    path("main/teumteum/<int:execution_id>/rate", CourseViewSet.as_view({"post": "rate"}), name="course-rate"),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)