from django.urls import path
from .views import RecordListView

urlpatterns = [
    path('', RecordListView.as_view(), name='record-list'),
]