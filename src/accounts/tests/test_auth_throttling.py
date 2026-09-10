from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.request import Request

from accounts.tests.factories import UserFactory
from accounts.throttles import ApiMutationThrottle, AuthSecurityThrottle

TEST_REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.CookieOrHeaderJWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": ("accounts.throttles.AuthSecurityThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "auth_security": "2/min",
    },
}


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
def test_login_throttling_returns_429(api_client, monkeypatch):
    cache.clear()
    monkeypatch.setattr(AuthSecurityThrottle, "rate", "2/min", raising=False)
    payload = {"username": "missing", "password": "wrong"}

    api_client.post("/api/auth/jwt/create/", payload, format="json")
    api_client.post("/api/auth/jwt/create/", payload, format="json")
    response = api_client.post("/api/auth/jwt/create/", payload, format="json")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
def test_successful_login_is_throttled_too(api_client, monkeypatch):
    cache.clear()
    monkeypatch.setattr(AuthSecurityThrottle, "rate", "2/min", raising=False)
    user = UserFactory.create(username="rapid-player", password="test-password")
    payload = {"username": user.username, "password": "test-password"}

    first = api_client.post("/api/auth/jwt/create/", payload, format="json")
    second = api_client.post("/api/auth/jwt/create/", payload, format="json")
    response = api_client.post("/api/auth/jwt/create/", payload, format="json")

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
def test_refresh_throttling_returns_429(api_client, monkeypatch):
    cache.clear()
    monkeypatch.setattr(AuthSecurityThrottle, "rate", "2/min", raising=False)
    user = UserFactory.create(username="player1", password="test-password")

    login = api_client.post(
        "/api/auth/jwt/create/",
        {"username": user.username, "password": "test-password"},
        format="json",
    )

    assert login.status_code == status.HTTP_200_OK

    refresh = login.data["refresh"]

    first = api_client.post(
        "/api/auth/jwt/refresh/",
        {"refresh": refresh},
        format="json",
    )

    second = api_client.post(
        "/api/auth/jwt/refresh/",
        {"refresh": first.data["refresh"]},
        format="json",
    )

    response = api_client.post(
        "/api/auth/jwt/refresh/",
        {"refresh": second.data["refresh"]},
        format="json",
    )

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
def test_password_reset_throttling_returns_429(api_client, monkeypatch):
    cache.clear()
    monkeypatch.setattr(AuthSecurityThrottle, "rate", "2/min", raising=False)
    payload = {"email": "missing@example.com"}

    api_client.post("/api/auth/users/reset-password/", payload, format="json")
    api_client.post("/api/auth/users/reset-password/", payload, format="json")

    response = api_client.post(
        "/api/auth/users/reset-password/",
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/jwt/create/",
        "/api/auth/jwt/refresh/",
        "/api/auth/users/",
        "/api/auth/users/set-password/",
        "/api/auth/users/reset-password/",
        "/api/auth/users/reset-password-confirm/",
    ],
)
def test_all_sensitive_auth_paths_are_throttled(path, rf):
    request = Request(
        rf.post(
            path,
            {"email": "player@example.com"},
            content_type="application/json",
        ),
        parsers=[JSONParser()],
    )

    request.user = None

    throttle = AuthSecurityThrottle()

    assert throttle.get_cache_key(request, None) is not None


def test_api_mutation_throttle_covers_profile_write(rf):
    user = UserFactory.build(pk=123)
    request = Request(rf.post("/api/profile/", {}, content_type="application/json"))
    request.user = user

    throttle = ApiMutationThrottle()

    assert throttle.get_cache_key(request, None) is not None


def test_api_mutation_throttle_skips_safe_profile_read(rf):
    user = UserFactory.build(pk=123)
    request = Request(rf.get("/api/profile/"))
    request.user = user

    throttle = ApiMutationThrottle()

    assert throttle.get_cache_key(request, None) is None


@pytest.mark.unit
def test_api_mutation_throttle_covers_profile_edit(rf):
    throttle = ApiMutationThrottle()
    request = Request(rf.patch("/api/profile/", {}, content_type="application/json"))
    request.user = SimpleNamespace(is_authenticated=True, pk=42)

    assert throttle.get_cache_key(request, None) == throttle.cache_format % {
        "scope": throttle.scope,
        "ident": "user:42",
    }
