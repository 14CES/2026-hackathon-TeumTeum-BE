import pytest
from django.urls import reverse
from records.models import Record
from accounts.models import User

@pytest.mark.django_db
def test_onboarding_success(api_client, test_user):
    # Given
    url = reverse('onboarding-answers')  # 온보딩 URL name 확인
    payload = {
        "guest_uuid": test_user.guest_uuid,
        "answers": [
            {"question_id": 1, "option_ids": [1]},
            {"question_id": 2, "option_ids": [4]},
            {"question_id": 3, "option_ids": [8]}
        ]
    }
    
    # When
    response = api_client.post(url, payload, format='json')
    
    # Then
    assert response.status_code == 201
    assert response.data["guest_uuid"] == test_user.guest_uuid


@pytest.mark.django_db
def test_onboarding_invalid_uuid(api_client):
    url = reverse('onboarding-answers')
    payload = {
        "guest_uuid": "invalid-uuid-1234",
        "answers": [{"question_id": 1, "option_ids": [1]}]
    }
    
    # When
    response = api_client.post(url, payload, format='json')
    
    # Then (400 Bad Request 검증)
    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_access_others_record(api_client, test_user):
    # Given: 다른 유저(other_user)의 기록 생성
    other_user = User.objects.create(guest_uuid="11111111-1111-1111-1111-111111111111")
    other_record = Record.objects.create(
        user=other_user,
        category="BODY",
        target_minutes=5,
        completed_minutes=5
    )
    
    url = f"/records/{other_record.id}/teumteum/"
    payload = {"guest_uuid": test_user.guest_uuid}
    
    # When
    response = api_client.post(url, payload, format='json')
    
    # Then: 403 Forbidden 반환 검증
    assert response.status_code == 403
    assert response.data["detail"] == "해당 기록에 접근할 권한이 없습니다."