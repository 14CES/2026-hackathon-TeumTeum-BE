from django.urls import path
from .views import OnboardingQuestionView, OnboardingAnswerView

urlpatterns = [
    path('questions', OnboardingQuestionView.as_view(), name='onboarding-questions'),
    
    path('', OnboardingAnswerView.as_view(), name='onboarding-answers'),
]