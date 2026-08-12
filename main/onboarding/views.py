from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import OnboardingSerializer

class OnboardingView(APIView):
    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            response_data["message"] = "온보딩 정보가 저장되었습니다."
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)