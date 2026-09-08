import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from accounts.models import PlayerProfile
from accounts.tests.factories import PlayerProfileFactory, UserFactory


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_account_registration_creates_user_without_player_profile(api_client):
    payload = {
        "username": "newplayer",
        "email": "newplayer@example.com",
        "password": "Example-Password-42",
    }

    response = api_client.post(
        "/api/auth/users/",
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    user = get_user_model().objects.get(username=payload["username"])

    assert user.email == payload["email"]
    assert user.check_password(payload["password"])
    assert not PlayerProfile.objects.filter(user=user).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_login_returns_access_and_refresh(api_client):
    user = UserFactory.create(
        username="player1",
        password="test-password",
    )

    response = api_client.post(
        "/api/auth/jwt/create/",
        {
            "username": user.username,
            "password": "test-password",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_refresh_token_returns_new_access_token(api_client):
    user = UserFactory.create(
        username="player1",
        password="test-password",
    )

    login_response = api_client.post(
        "/api/auth/jwt/create/",
        {
            "username": user.username,
            "password": "test-password",
        },
        format="json",
    )

    refresh_response = api_client.post(
        "/api/auth/jwt/refresh/",
        {
            "refresh": login_response.data["refresh"],
        },
        format="json",
    )

    assert refresh_response.status_code == status.HTTP_200_OK
    assert "access" in refresh_response.data


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_profile_without_access_token_returns_401(api_client):
    response = api_client.get("/api/profile/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_authenticated_user_gets_own_profile(api_client):
    user = UserFactory.create()
    profile = PlayerProfileFactory.create(user=user)

    api_client.force_authenticate(user=user)

    response = api_client.get("/api/profile/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == profile.id
    assert response.data["display_name"] == profile.display_name


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_authenticated_user_without_profile_gets_404(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/profile/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client):
    user = UserFactory.create(
        username="player1",
        password="test-password",
    )

    login_response = api_client.post(
        "/api/auth/jwt/create/",
        {
            "username": user.username,
            "password": "test-password",
        },
        format="json",
    )

    access = login_response.data["access"]
    refresh = login_response.data["refresh"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    logout_response = api_client.post(
        "/api/auth/logout/",
        {"refresh": refresh},
        format="json",
    )

    assert logout_response.status_code == status.HTTP_204_NO_CONTENT

    api_client.credentials()

    refresh_response = api_client.post(
        "/api/auth/jwt/refresh/",
        {"refresh": refresh},
        format="json",
    )

    assert refresh_response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_user_cannot_logout_with_another_users_refresh_token(api_client):
    user_a = UserFactory.create(
        username="player_a",
        password="test-password",
    )

    user_b = UserFactory.create(
        username="player_b",
        password="test-password",
    )

    login_a = api_client.post(
        "/api/auth/jwt/create/",
        {
            "username": user_a.username,
            "password": "test-password",
        },
        format="json",
    )

    login_b = api_client.post(
        "/api/auth/jwt/create/",
        {
            "username": user_b.username,
            "password": "test-password",
        },
        format="json",
    )

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_a.data['access']}")

    logout_response = api_client.post(
        "/api/auth/logout/",
        {"refresh": login_b.data["refresh"]},
        format="json",
    )

    assert logout_response.status_code == status.HTTP_400_BAD_REQUEST

    api_client.credentials()

    refresh_response = api_client.post(
        "/api/auth/jwt/refresh/",
        {"refresh": login_b.data["refresh"]},
        format="json",
    )

    assert refresh_response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_logout_without_access_token_returns_401(api_client):
    response = api_client.post(
        "/api/auth/logout/",
        {"refresh": "anything"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_logout_without_refresh_token_returns_400(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/auth/logout/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
