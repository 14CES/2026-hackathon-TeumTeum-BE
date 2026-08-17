import pytest
from uuid import uuid4
from rest_framework.test import APIClient

from accounts.models import User
from teumteum.models import Course, CourseContent


@pytest.mark.django_db
def test_create_course_api(monkeypatch):

    # Given
    user = User.objects.create(
        guest_uuid=str(uuid4()),
        target_minutes=30,
    )

    client = APIClient()

    def mock_get_user_context(user):
        return {
            "onboarding_status": ["휴식 중"],
            "categories": ["읽기"],
            "topics": ["몸"],
            "main_situation": "카페·실내",
            "other_content": None,
            "content_types": ["읽기", "스트레칭"],
            "next_schedule": "귀가·휴식",
            "next_schedule_other_content": None,
            "current_state": ["몸이 뻐근해요"],
            "target_minutes": 30,
        }

    def mock_get_recommended_contents(user):
        return {
            "articles": [
                {
                    "source_article_id": 1,
                    "title": "웰니스 원문 1",
                    "content": "웰니스 원문 1 본문",
                    "source": "틈틈 웰니스 노트",
                    "original_estimated_minutes": 10,
                    "estimated_minutes": 10,
                },
                {
                    "source_article_id": 2,
                    "title": "웰니스 원문 2",
                    "content": "웰니스 원문 2 본문",
                    "source": "틈틈 웰니스 노트",
                    "original_estimated_minutes": 10,
                    "estimated_minutes": 10,
                },
            ],
            "youtube": [
                {
                    "video_id": "test123",
                    "title": "스트레칭 영상",
                    "channel": "테스트 채널",
                    "thumbnail": "https://example.com/thumb.jpg",
                    "url": "https://youtube.com/watch?v=test123",
                    "estimated_minutes": 10,
                }
            ],
        }

    def mock_generate_personalized_brief(source_content, source_title, situation, interests, estimated_minutes):
        return {
            "title": source_title,
            "content": source_content,
            "action_tip": "테스트 실천 팁",
            "question": "테스트 질문",
        }

    monkeypatch.setattr(
        "teumteum.views.get_user_context",
        mock_get_user_context,
    )

    monkeypatch.setattr(
        "teumteum.views.get_recommended_contents",
        mock_get_recommended_contents,
    )

    monkeypatch.setattr(
        "teumteum.views.generate_personalized_brief",
        mock_generate_personalized_brief,
    )

    # When
    response = client.post(
        "/main/teumteum",
        {
            "guest_uuid": user.guest_uuid,
        },
        format="json",
    )

    # Then
    assert response.status_code == 201

    data = response.json()

    assert data["guest_uuid"] == user.guest_uuid
    assert data["target_minutes"] == 30

    assert "course" in data
    assert data["course"]["title"] == "30분 틈 활용법"
    assert data["course"]["total_minutes"] == 30

    assert len(data["course"]["contents"]) == 3

    assert Course.objects.filter(user=user).count() == 1
    assert CourseContent.objects.filter(
        course__user=user
    ).count() == 3