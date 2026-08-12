from django.shortcuts import render

# Create your views here.

from rest_framework.decorators import api_view
from rest_framework.response import Response
from services.news import get_news
from services.youtube import search_youtube


@api_view(["GET"])
def test_youtube(request):
    videos = search_youtube("10분 스트레칭")

    return Response(videos)