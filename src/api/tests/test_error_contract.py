import logging

import pytest
from rest_framework import status

from accounts.tests.factories import UserFactory
from api.exception_handler import api_exception_handler
from common.errors import domain_error


@pytest.mark.unit
def test_domain_error_has_stable_code_and_message():
    response = domain_error("NOT_YOUR_TURN", status.HTTP_403_FORBIDDEN)

    assert response.data == {
        "code": "NOT_YOUR_TURN",
        "message": "This action is not available outside your turn.",
    }


@pytest.mark.unit
def test_unhandled_exception_returns_safe_correlated_error(caplog):
    exc = RuntimeError("secret internal failure")

    with caplog.at_level(logging.ERROR, logger="api.exception_handler"):
        response = api_exception_handler(exc, {})

    correlation_id = response.data["details"]["correlation_id"]

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["code"] == "INTERNAL_ERROR"
    assert response.data["message"] == "The request could not be completed."
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
