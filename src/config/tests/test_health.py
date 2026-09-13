import pytest
from django.test import Client

from config import health


@pytest.fixture
def client():
    return Client()


def test_liveness_does_not_probe_dependencies(client, monkeypatch):
    def fail_if_called() -> bool:
        raise AssertionError("Liveness must not probe external dependencies.")

    monkeypatch.setattr(health, "_database_ready", fail_if_called)
    monkeypatch.setattr(health, "_redis_ready", fail_if_called)

    response = client.get("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("database_ready", "redis_ready"),
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_readiness_returns_503_when_dependency_is_unavailable(
    client,
    monkeypatch,
    database_ready,
    redis_ready,
):
    monkeypatch.setattr(health, "_database_ready", lambda: database_ready)
    monkeypatch.setattr(health, "_redis_ready", lambda: redis_ready)

    response = client.get("/health/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_readiness_returns_200_when_dependencies_are_ready(client, monkeypatch):
    monkeypatch.setattr(health, "_database_ready", lambda: True)
    monkeypatch.setattr(health, "_redis_ready", lambda: True)

    response = client.get("/health/ready/")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
