from unittest.mock import Mock

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.db import transaction
from django.test import Client
from django.utils import timezone

from accounts.jwt import SessionTokenObtainPairSerializer
from accounts.models import SessionFamily
from accounts.tests.factories import PlayerProfileFactory, UserFactory
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import (
    EventMode,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import (
    Game,
    GameParticipant,
    Round,
    Tournament,
    TournamentOrganizer,
    TournamentParticipant,
)
from tournaments.realtime.publisher import (
    organizer_group_name,
    participant_group_name,
    publish_realtime_event,
    table_group_name,
)
from tournaments.services.dice.roll_dice import execute_roll
from tournaments.services.tournament_lifecycle import start_tournament
from tournaments.tests.helpers import FakeRandomizer


@pytest.fixture
def asgi_application():
    from config.asgi import application

    return application


def _headers_for(user):
    refresh = SessionTokenObtainPairSerializer.get_token(user)
    access = str(refresh.access_token)

    return [
        (b"origin", b"http://localhost"),
        (b"cookie", f"access_token={access}".encode()),
    ]


def _anonymous_headers():
    return [(b"origin", b"http://localhost")]


async def _connect_then_close_code(communicator: WebsocketCommunicator) -> int:
    connected, _subprotocol = await communicator.connect()
    assert connected is True

    output = await communicator.receive_output(timeout=1)
    assert output["type"] == "websocket.close"
    return output["code"]


@pytest.mark.unit
def test_realtime_event_contract_is_minimal():
    event = {"type": "table_changed", "table_id": 12, "state_version": 4}

    assert set(event) == {"type", "table_id", "state_version"}
    assert "state" not in event


@pytest.mark.django_db(transaction=True)
def test_committed_roll_advances_version_and_calls_injected_publisher(roll_setup):
    user, game, _turn = roll_setup()
    publisher = Mock()

    execute_roll(
        user=user,
        game_id=game.pk,
        payload={},
        key="realtime-roll",
        rng=FakeRandomizer([1, 2, 3, 4, 5]),
        publisher=publisher,
    )

    game.refresh_from_db()
    assert game.state_version == 1

    publisher.assert_called_once()
    event_type, payload = publisher.call_args.args

    assert event_type == "table_changed"
    assert payload["game_id"] == game.pk
    assert payload["state_version"] == 1


@pytest.mark.django_db(transaction=True)
def test_rollback_reverts_state_version_and_does_not_publish(roll_setup):
    user, game, _turn = roll_setup()
    publisher = Mock()

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            execute_roll(
                user=user,
                game_id=game.pk,
                payload={},
                key="realtime-rollback",
                rng=FakeRandomizer([1, 2, 3, 4, 5]),
                publisher=publisher,
            )

            raise RuntimeError("force rollback")

    game.refresh_from_db()
    assert game.state_version == 0
    publisher.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_delivery_failure_after_commit_does_not_undo_saved_roll(roll_setup):
    user, game, turn = roll_setup()
    failing_publisher = Mock(side_effect=RuntimeError("redis unavailable"))

    response = execute_roll(
        user=user,
        game_id=game.pk,
        payload={},
        key="realtime-delivery-failure",
        rng=FakeRandomizer([1, 2, 3, 4, 5]),
        publisher=failing_publisher,
    )

    game.refresh_from_db()

    assert response["roll_number"] == 1
    assert turn.rolls.count() == 1
    assert game.state_version == 1

    failing_publisher.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_publisher_targets_table_and_organizer_groups(roll_setup):
    _user, game, _turn = roll_setup()
    layer = get_channel_layer()
    table_channel = "test.table.receiver"
    organizer_channel = "test.organizer.received"

    async_to_sync(layer.group_add)(table_group_name(game.pk), table_channel)

    async_to_sync(layer.group_add)(
        organizer_group_name(game.round.tournament_id), organizer_channel
    )

    publish_realtime_event(
        "table_changed",
        {"game_id": game.pk, "state_version": 7},
    )

    table_event = async_to_sync(layer.receive)(table_channel)
    organizer_event = async_to_sync(layer.receive)(organizer_channel)

    expected = {
        "type": "table.changed",
        "table_id": game.pk,
        "state_version": 7,
    }

    assert table_event == expected
    assert organizer_event == expected


@pytest.mark.django_db(transaction=True)
def test_anonymous_websocket_is_rejected(asgi_application):
    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            "/ws/tables/999/",
            headers=_anonymous_headers(),
        )

        return await _connect_then_close_code(communicator)

    close_code = async_to_sync(scenario)()

    assert close_code == 4401


@pytest.mark.django_db(transaction=True)
def test_django_session_cookie_cannot_bypass_hardened_ws_auth(
    roll_setup,
    asgi_application,
):
    participant, game, _turn = roll_setup()
    client = Client()
    client.force_login(participant)
    session_cookie = client.cookies["sessionid"].value

    headers = [
        (b"origin", b"http://localhost"),
        (b"cookie", f"sessionid={session_cookie}".encode()),
    ]

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            f"/ws/tables/{game.pk}/",
            headers=headers,
        )

        return await _connect_then_close_code(communicator)

    close_code = async_to_sync(scenario)()

    assert close_code == 4401


@pytest.mark.django_db(transaction=True)
def test_assigned_participant_can_join_own_table(
    roll_setup,
    asgi_application,
):
    participant, game, _turn = roll_setup()
    headers = _headers_for(participant)

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            f"/ws/tables/{game.pk}/",
            headers=headers,
        )

        result = await communicator.connect()

        if result[0]:
            await communicator.disconnect()
        return result

    connected, _subprotocol = async_to_sync(scenario)()

    assert connected is True


@pytest.mark.django_db(transaction=True)
def test_open_socket_closes_when_session_family_expires(
    roll_setup,
    asgi_application,
    monkeypatch,
):
    participant, game, _turn = roll_setup()
    refresh = SessionTokenObtainPairSerializer.get_token(participant)

    access = str(refresh.access_token)
    family_id = refresh["session_family"]

    headers = [
        (b"origin", b"http://localhost"),
        (b"cookie", f"access_token={access}".encode()),
    ]

    monkeypatch.setattr(
        "tournaments.realtime.consumers.SESSION_RECHECK_SECONDS",
        0.01,
    )

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            f"/ws/tables/{game.pk}/",
            headers=headers,
        )

        connected, _subprotocol = await communicator.connect()
        assert connected is True

        await database_sync_to_async(SessionFamily.objects.filter(pk=family_id).update)(
            revoked_at=timezone.now()
        )

        output = await communicator.receive_output(timeout=1)
        return output

    output = async_to_sync(scenario)()

    assert output["type"] == "websocket.close"
    assert output["code"] == 4401


@pytest.mark.django_db(transaction=True)
def test_revoked_session_family_is_rejected(
    roll_setup,
    asgi_application,
):
    participant, game, _turn = roll_setup()
    refresh = SessionTokenObtainPairSerializer.get_token(participant)
    access = str(refresh.access_token)

    SessionFamily.objects.filter(pk=refresh["session_family"]).update(
        revoked_at=timezone.now()
    )

    headers = [
        (b"origin", b"http://localhost"),
        (
            b"cookie",
            f"access_token={access}".encode(),
        ),
    ]

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            f"/ws/tables/{game.pk}/",
            headers=headers,
        )

        return await _connect_then_close_code(communicator)

    close_code = async_to_sync(scenario)()

    assert close_code == 4401


@pytest.mark.django_db(transaction=True)
def test_user_from_another_table_is_rejected(
    roll_setup,
    asgi_application,
):
    _participant, game, _turn = roll_setup()
    other_user = UserFactory.create()
    headers = _headers_for(other_user)

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            f"/ws/tables/{game.pk}/",
            headers=headers,
        )

        return await _connect_then_close_code(communicator)

    close_code = async_to_sync(scenario)()

    assert close_code == 4403


@pytest.mark.django_db(transaction=True)
def test_organizer_without_participation_cannot_join_participant_table_socket(
    roll_setup,
    asgi_application,
):
    _participant, game, _turn = roll_setup()
    organizer = UserFactory.create()

    TournamentOrganizer.objects.create(
        tournament=game.round.tournament,
        user=organizer,
    )

    headers = _headers_for(organizer)

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            f"/ws/tables/{game.pk}/",
            headers=headers,
        )

        return await _connect_then_close_code(communicator)

    close_code = async_to_sync(scenario)()

    assert close_code == 4403


@pytest.mark.django_db(transaction=True)
def test_participant_assignment_socket_redirects_from_non_table_page(
    roll_setup,
    asgi_application,
):
    participant, game, _turn = roll_setup()
    headers = _headers_for(participant)

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            "/ws/participant/assignments/",
            headers=headers,
        )

        connected, _subprotocol = await communicator.connect()
        assert connected is True

        event = await communicator.receive_json_from()

        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()

    assert event == {
        "type": "table_assignment_changed",
        "table_id": game.pk,
        "state_version": game.state_version,
        "target_url": f"/tables/{game.pk}/",
    }


@pytest.mark.django_db(transaction=True)
def test_assignment_socket_waits_for_future_assignment_while_participant_is_elsewhere(
    roll_setup,
    asgi_application,
):
    participant, game, _turn = roll_setup()
    tournament_participant = game.game_participants.get().tournament_participant

    game.round.status = RoundStatus.WAITING
    game.round.save(update_fields=("status",))
    headers = _headers_for(participant)

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            "/ws/participant/assignments/",
            headers=headers,
        )

        connected, _subprotocol = await communicator.connect()
        assert connected is True

        layer = get_channel_layer()

        await layer.group_send(
            participant_group_name(tournament_participant.pk),
            {
                "type": "table.assignment_changed",
                "table_id": game.pk,
                "state_version": 3,
                "target_url": f"/tables/{game.pk}/",
            },
        )

        event = await communicator.receive_json_from()
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()

    assert event == {
        "type": "table_assignment_changed",
        "table_id": game.pk,
        "state_version": 3,
        "target_url": f"/tables/{game.pk}/",
    }


@pytest.mark.django_db(transaction=True)
def test_registered_participant_waiting_off_table_is_redirected_when_tournament_starts(
    asgi_application,
):
    profile = PlayerProfileFactory.create()
    other_profile = PlayerProfileFactory.create()

    tournament = Tournament.objects.create(
        name="Assignment Start Tournament",
        status=TournamentStatus.REGISTRATION,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
        max_participants=4,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=2,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.REMOTE,
    )

    participant = TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Waiting Player",
        display_name_snapshot="Waiting Player",
        starting_number=1,
    )

    TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=other_profile,
        full_name_snapshot="Other Player",
        display_name_snapshot="Other Player",
        starting_number=2,
    )

    headers = _headers_for(profile.user)

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            "/ws/participant/assignments/",
            headers=headers,
        )

        connected, _subprotocol = await communicator.connect()
        assert connected is True

        await database_sync_to_async(start_tournament)(
            tournament,
            publisher=publish_realtime_event,
        )

        event = await communicator.receive_json_from()
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    participant.refresh_from_db()
    assigned_game = participant.game_participations.get().game

    assert event == {
        "type": "table_assignment_changed",
        "table_id": assigned_game.pk,
        "state_version": assigned_game.state_version,
        "target_url": f"/tables/{assigned_game.pk}/",
    }


@pytest.mark.django_db(transaction=True)
def test_participant_cannot_join_organizer_group(
    roll_setup,
    asgi_application,
):
    participant, game, _turn = roll_setup()
    headers = _headers_for(participant)

    async def scenario():
        communicator = WebsocketCommunicator(
            asgi_application,
            f"/ws/tournaments/{game.round.tournament_id}/organizers/",
            headers=headers,
        )

        return await _connect_then_close_code(communicator)

    close_code = async_to_sync(scenario)()

    assert close_code == 4403


@pytest.mark.django_db(transaction=True)
def test_organizer_receives_same_table_event_on_multiple_devices(
    roll_setup,
    asgi_application,
):
    _participant, game, _turn = roll_setup()
    organizer = UserFactory.create()

    TournamentOrganizer.objects.create(
        tournament=game.round.tournament,
        user=organizer,
    )

    headers = _headers_for(organizer)

    async def scenario():
        path = f"/ws/tournaments/{game.round.tournament_id}/organizers/"
        first = WebsocketCommunicator(asgi_application, path, headers=headers)
        second = WebsocketCommunicator(asgi_application, path, headers=headers)

        assert (await first.connect())[0] is True
        assert (await second.connect())[0] is True

        layer = get_channel_layer()

        await layer.group_send(
            organizer_group_name(game.round.tournament_id),
            {
                "type": "table.changed",
                "table_id": game.pk,
                "state_version": 9,
            },
        )

        first_event = await first.receive_json_from()
        second_event = await second.receive_json_from()

        await first.disconnect()
        await second.disconnect()
        return first_event, second_event

    first_event, second_event = async_to_sync(scenario)()

    expected = {
        "type": "table_changed",
        "table_id": game.pk,
        "state_version": 9,
    }

    assert first_event == expected
    assert second_event == expected


@pytest.mark.django_db(transaction=True)
def test_round_transition_publishes_server_derived_assignment(roll_setup):
    user, first_game, _turn = roll_setup()
    participant = first_game.game_participants.get().tournament_participant

    layer = get_channel_layer()
    channel_name = "test.assignment.receiver"

    first_game.round.status = RoundStatus.COMPLETED
    first_game.round.save(update_fields=("status",))

    next_round = Round.objects.create(
        tournament=first_game.round.tournament,
        number=2,
        status=RoundStatus.ACTIVE,
    )

    next_game = Game.objects.create(
        round=next_round,
        display_number=1,
        allocation_seed=2,
        allocation_cost=0,
    )

    GameParticipant.objects.create(
        game=next_game,
        tournament_participant=participant,
        turn_order=1,
    )

    async_to_sync(layer.group_add)(participant_group_name(participant.pk), channel_name)

    publish_realtime_event("round_transition", {"round_id": next_round.pk})
    event = async_to_sync(layer.receive)(channel_name)

    assert event == {
        "type": "table.assignment_changed",
        "table_id": next_game.pk,
        "state_version": 0,
        "target_url": f"/tables/{next_game.pk}/",
    }

    assert participant.player_profile.user_id == user.pk
