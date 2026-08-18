from django.urls import path
from .views import MagazineRecommendationView, MagazineDetailView

urlpatterns = [
    path('', MagazineRecommendationView.as_view(), name='discovery-report'),
    path('discovery/<int:article_id>/', MagazineDetailView.as_view(), name='discovery-detail'),
]