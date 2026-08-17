from django.urls import path
from .views import MagazineRecommendationView

urlpatterns = [
    path('', MagazineRecommendationView.as_view(), name='discovery-report'),
]