from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import OnboardingAnswerSerializer

# 1. 온보딩 질문 목록 조회 API (GET /onboarding/questions/)
class OnboardingQuestionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            "questions": [
                {
                    "order": 1,
                    "question_id": 1,
                    "question": "요즘 가장 정비하고 싶은 틈은 어디인가요?",
                    "options": [
                        {"option_id": 1, "content": "마음-틈"},
                        {"option_id": 2, "content": "몸-틈"},
                        {"option_id": 3, "content": "준비-틈"}
                    ]
                },
                {
                    "order": 2,
                    "question_id": 2,
                    "question": "보통 어떤 순간에 '틈'이 찾아오나요?",
                    "options": [
                        {"option_id": 4, "content": "이동할 때"},
                        {"option_id": 5, "content": "약속 전에"},
                        {"option_id": 6, "content": "휴식할 때"},
                        {"option_id": 7, "content": "업무 및 공부 중에"}
                    ]
                },
                {
                    "order": 3,
                    "question_id": 3,
                    "question": "요즘 어떤 주제에 마음이 가시나요?",
                    "options": [
                        {"option_id": 8, "content": "트렌드·이슈"},
                        {"option_id": 9, "content": "멘탈 케어"},
                        {"option_id": 10, "content": "건강"},
                        {"option_id": 11, "content": "휴식"}
                    ]
                }
            ]
        }
        return Response(data, status=status.HTTP_200_OK)


# 2. 온보딩 답변 제출 API (POST /onboarding/)
class OnboardingAnswerView(APIView):
    permission_classes = [IsAuthenticated] # X-Guest-ID 헤더 검증

    def post(self, request):
        serializer = OnboardingAnswerSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                "guest_uuid": serializer.validated_data["guest_uuid"],
                "message": "온보딩 답변이 저장되었습니다."
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)