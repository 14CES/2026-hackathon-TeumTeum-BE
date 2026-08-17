from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import OnboardingAnswerSerializer

class OnboardingQuestionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            "questions": [
                {
                    "order": 1,
                    "question_id": 1,
                    "question": "평소 관심 있는 회복 방식은 무엇인가요?",
                    "options": [
                        {"option_id": 1, "content": "읽기"},
                        {"option_id": 2, "content": "듣기"},
                        {"option_id": 3, "content": "스트레칭"},
                        {"option_id": 4, "content": "마음 정리"}
                    ]
                },
                {
                    "order": 2,
                    "question_id": 2,
                    "question": "보통 어떤 순간에 '틈'이 찾아오나요?",
                    "description": "자주 마주치는 공백시간 상황을 알려주세요. (복수 선택 가능)",
                    "options": [
                        {"option_id": 5, "content": "이동 중"},
                        {"option_id": 6, "content": "약속 전"},
                        {"option_id": 7, "content": "휴식 중"},
                        {"option_id": 8, "content": "업무·수업 중"}
                    ]
                },
                {
                    "order": 3,
                    "question_id": 3,
                    "question": "요즘 어떤 웰니스에 마음이 가시나요?",
                    "options": [
                        {"option_id": 9, "content": "피부"},
                        {"option_id": 10, "content": "몸"},
                        {"option_id": 11, "content": "마음"},
                        {"option_id": 12, "content": "수면"}
                    ]
                }
            ]
        }
        return Response(data, status=status.HTTP_200_OK)


class OnboardingAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OnboardingAnswerSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                "guest_uuid": serializer.validated_data["guest_uuid"],
                "message": "온보딩 답변이 저장되었습니다."
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)