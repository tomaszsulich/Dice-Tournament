from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.models import SessionFamily
from accounts.services.session_activity import (
    SessionRejected,
    create_session_family,
    record_activity,
    validate_session_family,
)
from accounts.tests.factories import PlayerProfileFactory, UserFactory


class FrozenClock:
    def __init__(self, now: datetime):
        self.current = now

    def now(self):
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_session_family_keeps_original_eight_hour_boundary():
    user = UserFactory.create(password="test-password")

    start = datetime(2026, 9, 7, 12, 0, tzinfo=dt_timezone.utc)
    clock = FrozenClock(start)

    family = create_session_family(user=user, clock=clock)
    clock.advance(timedelta(hours=7, minutes=59))

    family.last_activity_at = clock.now()
    family.save(update_fields=["last_activity_at"])

    validate_session_family(family_id=family.pk, clock=clock)
    clock.advance(timedelta(minutes=1))

    with pytest.raises(SessionRejected, match="SESSION_EXPIRED"):
        validate_session_family(family_id=family.pk, clock=clock)


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_session_expires_after_thirty_minutes_without_activity():
    user = UserFactory.create(password="test-password")

    start = datetime(2026, 9, 7, 12, 0, tzinfo=dt_timezone.utc)
    clock = FrozenClock(start)

    family = create_session_family(user=user, clock=clock)
    clock.advance(timedelta(minutes=30))

    with pytest.raises(SessionRejected, match="SESSION_INACTIVE"):
        validate_session_family(family_id=family.pk, clock=clock)

    family.refresh_from_db()
    assert family.revoked_at == clock.now()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_record_activity_updates_last_activity():
    user = UserFactory.create(password="test-password")

    start = datetime(2026, 9, 7, 12, 0, tzinfo=dt_timezone.utc)
    clock = FrozenClock(start)

    family = create_session_family(user=user, clock=clock)

    clock.advance(timedelta(minutes=20))
    record_activity(family_id=family.pk, clock=clock)

    family.refresh_from_db()
    assert family.last_activity_at == clock.now()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_access_token_lifetime_is_fifteen_minutes(api_client):
    user = UserFactory.create(username="player1", password="test-password")

    login = api_client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    access = AccessToken(login.data["access"])
    assert access["exp"] - access["iat"] == 15 * 60


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_refresh_rotation_does_not_extend_family_expiry(api_client):
    user = UserFactory.create(username="player1", password="test-password")

    login = api_client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    old_refresh = RefreshToken(login.data["refresh"])
    family = SessionFamily.objects.get(pk=old_refresh["session_family"])

    refreshed = api_client.post(
        "/api/auth/jwt/refresh/",
        {"refresh": login.data["refresh"]},
        format="json",
    )

    assert refreshed.status_code == status.HTTP_200_OK

    rotated = RefreshToken(refreshed.data["refresh"])

    assert rotated["session_family"] == str(family.pk)
    assert rotated["exp"] == int(family.absolute_expires_at.timestamp())


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_reusing_rotated_refresh_revokes_whole_family(api_client):
    user = UserFactory.create(username="player1", password="test-password")

    login = api_client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    original = login.data["refresh"]

    family = SessionFamily.objects.get(
        pk=RefreshToken(original)["session_family"],
    )

    first_refresh = api_client.post(
        "/api/auth/jwt/refresh/", {"refresh": original}, format="json"
    )

    assert first_refresh.status_code == status.HTTP_200_OK

    reused = api_client.post(
        "/api/auth/jwt/refresh/", {"refresh": original}, format="json"
    )

    assert reused.status_code == status.HTTP_400_BAD_REQUEST

    family.refresh_from_db()
    assert family.revoked_at is not None

    rotated_after_reuse = api_client.post(
        "/api/auth/jwt/refresh/",
        {"refresh": first_refresh.data["refresh"]},
        format="json",
    )

    assert rotated_after_reuse.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_cookie_refresh_requires_csrf():
    client = APIClient(enforce_csrf_checks=True)
    user = UserFactory.create(username="player1", password="test-password")

    login = client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    no_csrf = client.post("/api/auth/jwt/refresh/", {}, format="json")
    assert no_csrf.status_code == status.HTTP_403_FORBIDDEN

    client.credentials(HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    with_csrf = client.post("/api/auth/jwt/refresh/", {}, format="json")

    assert with_csrf.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_body_refresh_does_not_require_csrf():
    user = UserFactory.create(username="player1", password="test-password")

    login = APIClient().post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    refreshed = APIClient(enforce_csrf_checks=True).post(
        "/api/auth/jwt/refresh/",
        {"refresh": login.data["refresh"]},
        format="json",
    )

    assert refreshed.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_bearer_authenticated_logout_does_not_require_csrf():
    user = UserFactory.create(username="player1", password="test-password")

    login = APIClient().post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    client = APIClient(enforce_csrf_checks=True)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = client.post(
        "/api/auth/logout/",
        {"refresh": login.data["refresh"]},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_cookie_refresh_does_not_update_last_activity():
    client = APIClient(enforce_csrf_checks=True)
    user = UserFactory.create(username="player1", password="test-password")

    login = client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    family = SessionFamily.objects.get(
        pk=RefreshToken(login.data["refresh"])["session_family"],
    )

    original_activity = timezone.now() - timedelta(minutes=10)
    family.last_activity_at = original_activity
    family.save(update_fields=["last_activity_at"])

    client.credentials(HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    refreshed = client.post("/api/auth/jwt/refresh/", {}, format="json")

    assert refreshed.status_code == status.HTTP_200_OK

    family.refresh_from_db()
    assert family.last_activity_at == original_activity


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_cookie_authenticated_profile_edit_requires_csrf():
    client = APIClient(enforce_csrf_checks=True)
    user = UserFactory.create(username="profile-player", password="test-password")

    PlayerProfileFactory.create(
        user=user,
        display_name="Before",
        nickname="OldNick",
    )

    login = client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    no_csrf = client.patch(
        "/api/profile/",
        {"display_name": "After"},
        format="json",
    )

    assert no_csrf.status_code == status.HTTP_403_FORBIDDEN

    client.credentials(HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)

    with_csrf = client.patch(
        "/api/profile/",
        {"display_name": "After"},
        format="json",
    )

    assert with_csrf.status_code == status.HTTP_200_OK
