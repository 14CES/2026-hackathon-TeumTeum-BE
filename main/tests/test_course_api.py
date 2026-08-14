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
            "onboarding_status": ["휴식할 때"],
            "categories": ["마음-틈"],
            "topics": ["멘탈 케어"],
            "main_situation": "카페/실내",
            "other_content": None,
            "content_types": ["독서", "스트레칭"],
            "target_minutes": 30,
        }

    def mock_get_recommended_contents(user):
        return {
            "news": [
                {
                    "title": "뉴스 1",
                    "description": "뉴스 설명 1",
                    "source": "테스트 출처",
                    "url": "https://example.com/news1",
                    "image_url": "https://example.com/news1.jpg",
                    "estimated_minutes": 10,
                },
                {
                    "title": "뉴스 2",
                    "description": "뉴스 설명 2",
                    "source": "테스트 출처",
                    "url": "https://example.com/news2",
                    "image_url": "https://example.com/news2.jpg",
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

    monkeypatch.setattr(
        "teumteum.views.get_user_context",
        mock_get_user_context,
    )

    monkeypatch.setattr(
        "teumteum.views.get_recommended_contents",
        mock_get_recommended_contents,
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