import pytest
from rest_framework import status

from tournaments.domain.tournament.types import EventMode
from tournaments.models import Roll


@pytest.mark.django_db
def test_roll_api_requires_authentication(api_client, roll_setup):
    _user, game, _turn = roll_setup()

    response = api_client.post(
        f"/api/games/{game.pk}/roll/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="key-1",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_stationary_roll_api_replays_same_idempotency_key(api_client, roll_setup):
    user, game, _turn = roll_setup(EventMode.IN_PERSON)
    api_client.force_authenticate(user=user)

    request = {
        "path": f"/api/games/{game.pk}/roll/",
        "data": {"values": [1, 2, 3, 4, 5]},
        "format": "json",
        "HTTP_IDEMPOTENCY_KEY": "physical-retry",
    }

    first = api_client.post(**request)
    second = api_client.post(**request)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED
    assert second.data == first.data
    assert Roll.objects.filter(turn__game_participant__game=game).count() == 1


@pytest.mark.django_db
def test_stationary_roll_api_returns_409_for_changed_payload_same_key(
    api_client,
    roll_setup,
):
    user, game, _turn = roll_setup(EventMode.IN_PERSON)
    api_client.force_authenticate(user=user)
    path = f"/api/games/{game.pk}/roll/"

    api_client.post(
        path,
        {"values": [1, 2, 3, 4, 5]},
        format="json",
        HTTP_IDEMPOTENCY_KEY="conflict",
    )

    response = api_client.post(
        path,
        {"values": [6, 2, 3, 4, 5]},
        format="json",
        HTTP_IDEMPOTENCY_KEY="conflict",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "IDEMPOTENCY_CONFLICT"
