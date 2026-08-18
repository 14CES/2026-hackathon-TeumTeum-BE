import pytest
from rest_framework.test import APIClient
from accounts.models import User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user(db):
    return User.objects.create(guest_uuid="550e8400-e29b-41d4-a716-446655440000")