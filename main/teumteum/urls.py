from django.urls import path, include
from . import views
from .views import *
from rest_framework import routers

from django.conf import settings
from django.conf.urls.static import static

app_name = "teumteum"

default_router = routers.SimpleRouter(trailing_slash=False)

default_router.register("main", MainViewSet, basename="main")
default_router.register("main/questions", MainQuestionViewSet, basename="questions")

urlpatterns = [
    path("", include(default_router.urls)),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)