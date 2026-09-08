import re

import pytest
from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import SessionFamily
from accounts.tests.factories import UserFactory

TEST_MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    },
}


def _extract_reset_credentials(message_body: str) -> tuple[str, str]:
    match = re.search(
        r"set-password/\?uid=(?P<uid>[^&\s]+)&token=(?P<token>[^\s]+)",
        message_body,
    )

    assert match is not None
    return match.group("uid"), match.group("token")


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_authenticated_user_can_change_password_and_sessions_are_revoked(api_client):
    user = UserFactory.create(username="player1", password="Old-Password-42")

    login = api_client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "Old-Password-42"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    family = SessionFamily.objects.get(
        pk=RefreshToken(login.data["refresh"])["session_family"],
    )

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = api_client.post(
        "/api/auth/users/set-password/",
        {
            "current_password": "Old-Password-42",
            "new_password": "New-Password-84",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    user.refresh_from_db()
    family.refresh_from_db()

    assert user.check_password("New-Password-84")
    assert family.revoked_at is not None


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(MAILERS=TEST_MAILERS)
def test_password_reset_email_confirms_once_and_revokes_sessions(api_client):
    mail.outbox = []

    user = UserFactory.create(
        username="player1",
        email="player1@example.com",
        password="Old-Password-42",
    )

    login = api_client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "Old-Password-42"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    family = SessionFamily.objects.get(
        pk=RefreshToken(login.data["refresh"])["session_family"],
    )

    reset = api_client.post(
        "/api/auth/users/reset-password/",
        {"email": user.email},
        format="json",
    )

    assert reset.status_code == status.HTTP_204_NO_CONTENT
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]

    uid, token = _extract_reset_credentials(mail.outbox[0].body)

    payload = {
        "uid": uid,
        "token": token,
        "new_password": "New-Password-84",
    }

    confirmed = api_client.post(
        "/api/auth/users/reset-password-confirm/",
        payload,
        format="json",
    )

    assert confirmed.status_code == status.HTTP_204_NO_CONTENT

    user.refresh_from_db()
    family.refresh_from_db()

    assert user.check_password("New-Password-84")
    assert family.revoked_at is not None

    api_client.cookies.clear()

    reused = api_client.post(
        "/api/auth/users/reset-password-confirm/",
        payload,
        format="json",
    )

    assert reused.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(MAILERS=TEST_MAILERS)
def test_password_reset_does_not_reveal_unknown_email(api_client):
    mail.outbox = []

    response = api_client.post(
        "/api/auth/users/reset-password/",
        {"email": "missing@example.com"},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert mail.outbox == []
