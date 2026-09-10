import logging

import pytest
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from accounts.tests.factories import UserFactory
from api.exception_handler import api_exception_handler
from common.errors import domain_error


@pytest.mark.unit
def test_domain_error_has_stable_code_and_message():
    response = domain_error("NOT_YOUR_TURN", status.HTTP_403_FORBIDDEN)

    assert response.data == {
        "code": "NOT_YOUR_TURN",
        "message": "Not your turn.",
    }


@pytest.mark.unit
def test_domain_forbidden_and_csrf_forbidden_keep_distinct_contracts():
    domain = domain_error("NOT_YOUR_TURN", status.HTTP_403_FORBIDDEN)
    csrf = api_exception_handler(PermissionDenied("CSRF Failed: token missing."), {})

    assert domain.status_code == status.HTTP_403_FORBIDDEN
    assert domain.data["code"] == "NOT_YOUR_TURN"
    assert "detail" not in domain.data

    assert csrf.status_code == status.HTTP_403_FORBIDDEN
    assert "code" not in csrf.data
    assert str(csrf.data["detail"]).startswith("CSRF Failed:")


@pytest.mark.unit
def test_unhandled_exception_returns_safe_correlated_error(caplog):
    exc = RuntimeError("secret internal failure")

    with caplog.at_level(logging.ERROR, logger="api.exception_handler"):
        response = api_exception_handler(exc, {})

    correlation_id = response.data["details"]["correlation_id"]

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["code"] == "INTERNAL_ERROR"
    assert response.data["message"] == "Request failed."
    assert "secret internal failure" not in str(response.data)

    assert correlation_id
    assert correlation_id in caplog.text
    assert "RuntimeError: secret internal failure" in caplog.text


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_game_not_found_uses_domain_error_contract(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/games/999999/state/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["code"] == "GAME_NOT_FOUND"
    assert isinstance(response.data["message"], str)


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_validation_errors_keep_standard_drf_representation(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/tournaments/?available_to_join=false")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "available_to_join" in response.data
    assert "code" not in response.data


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_openapi_schema_requires_admin(api_client):
    user = UserFactory.create(is_staff=False)
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/schema/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_openapi_documents_security_and_domain_refusals_for_mvp_commands(api_client):
    staff = UserFactory.create(is_staff=True)
    api_client.force_authenticate(user=staff)

    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == status.HTTP_200_OK
    schema = response.data

    expected_responses = {
        "/api/auth/jwt/create/": {"200", "400", "401", "403", "429", "500"},
        "/api/auth/jwt/refresh/": {"200", "400", "401", "403", "429", "500"},
        "/api/auth/logout/": {"204", "400", "401", "403", "429", "500"},
        "/api/auth/users/": {"201", "400", "403", "429", "500"},
        "/api/auth/users/set-password/": {"204", "400", "401", "403", "429", "500"},
        "/api/auth/users/reset-password/": {"204", "400", "403", "429", "500"},
        "/api/auth/users/reset-password-confirm/": {"204", "400", "403", "429", "500"},
        "/api/profile/": {"200", "201", "400", "401", "403", "409", "429", "500"},
        "/api/games/{game_id}/roll/": {
            "201",
            "400",
            "401",
            "403",
            "404",
            "409",
            "429",
            "500",
        },
        "/api/games/{game_id}/holds/": {
            "200",
            "400",
            "401",
            "403",
            "404",
            "409",
            "429",
            "500",
        },
        "/api/games/{game_id}/choose-category/": {
            "201",
            "400",
            "401",
            "403",
            "404",
            "409",
            "429",
            "500",
        },
        "/api/tournaments/create/": {"201", "400", "401", "403", "429", "500"},
    }

    for path, expected in expected_responses.items():
        operation = schema["paths"][path]["post"]
        assert expected <= set(operation["responses"]), path
