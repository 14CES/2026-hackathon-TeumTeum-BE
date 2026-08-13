from django.urls import path
from .views import RecordListView, RecordReentryView

urlpatterns = [
    path('', RecordListView.as_view(), name='record-list'),
    path('<int:record_id>/teumteum/', RecordReentryView.as_view(), name='record-reentry'),
]