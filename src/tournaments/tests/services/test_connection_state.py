from datetime import timedelta

import pytest
from django.utils import timezone

from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import (
    ParticipantConnectionStatus,
    ParticipantStatus,
)
from tournaments.models import Game, GameParticipant, Round, TournamentParticipant
from tournaments.services.connection_state import (
    RECONNECT_GRACE,
    decision_deadline_for,
    mark_connected,
    mark_reconnecting,
    official_game_for_participant,
    refresh_connection_status,
)


@pytest.mark.django_db
def test_connection_grace_becomes_disconnected_without_removing_participant(roll_setup):
    user, game, _turn = roll_setup()
    participant = TournamentParticipant.objects.get(player_profile__user=user)
    disconnected_at = timezone.now()

    assert mark_connected(participant_id=participant.pk, channel_name="channel-a")

    assert mark_reconnecting(
        participant_id=participant.pk,
        channel_name="channel-a",
        now=disconnected_at,
    )

    participant.refresh_from_db()

    assert participant.connection_status == ParticipantConnectionStatus.RECONNECTING
    assert participant.status == ParticipantStatus.ACTIVE

    before_grace = disconnected_at + RECONNECT_GRACE - timedelta(milliseconds=1)

    assert (
        refresh_connection_status(participant_id=participant.pk, now=before_grace)
        == ParticipantConnectionStatus.RECONNECTING
    )

    after_grace = disconnected_at + RECONNECT_GRACE

    assert (
        refresh_connection_status(participant_id=participant.pk, now=after_grace)
        == ParticipantConnectionStatus.DISCONNECTED
    )

    participant.refresh_from_db()

    assert participant.status == ParticipantStatus.ACTIVE
    assert participant.disconnected_at == disconnected_at
    assert official_game_for_participant(participant).pk == game.pk


@pytest.mark.django_db
def test_stale_socket_disconnect_does_not_override_new_connection(roll_setup):
    user, _game, _turn = roll_setup()
    participant = TournamentParticipant.objects.get(player_profile__user=user)

    assert mark_connected(participant_id=participant.pk, channel_name="old-channel")
    assert mark_connected(participant_id=participant.pk, channel_name="new-channel")

    assert not mark_reconnecting(
        participant_id=participant.pk,
        channel_name="old-channel",
    )

    participant.refresh_from_db()

    assert participant.connection_status == ParticipantConnectionStatus.CONNECTED
    assert participant.active_connection_channel == "new-channel"
    assert participant.disconnected_at is None


@pytest.mark.django_db
def test_inactive_participant_is_not_reactivated_by_reconnect(roll_setup):
    user, _game, _turn = roll_setup()

    participant = TournamentParticipant.objects.get(player_profile__user=user)
    participant.status = ParticipantStatus.WITHDRAWN
    participant.save(update_fields=("status",))

    assert not mark_connected(participant_id=participant.pk, channel_name="channel-a")

    participant.refresh_from_db()

    assert participant.status == ParticipantStatus.WITHDRAWN
    assert participant.connection_status == ParticipantConnectionStatus.DISCONNECTED


@pytest.mark.django_db
def test_official_assignment_is_latest_server_created_table(roll_setup):
    user, first_game, _turn = roll_setup()

    participant = TournamentParticipant.objects.get(player_profile__user=user)
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

    assert official_game_for_participant(participant) == next_game


@pytest.mark.django_db
def test_decision_deadline_uses_frozen_tournament_limit(roll_setup):
    _user, game, _turn = roll_setup()
    tournament = game.round.tournament
    now = timezone.now()

    tournament.decision_time_limit = 60
    assert decision_deadline_for(tournament, now=now) == now + timedelta(seconds=60)

    tournament.decision_time_limit = 0
    assert decision_deadline_for(tournament, now=now) is None


@pytest.mark.django_db
def test_reconnect_state_changes_do_not_reset_action_deadline(roll_setup):
    user, _game, turn = roll_setup()

    participant = TournamentParticipant.objects.get(player_profile__user=user)
    deadline = timezone.now() + timedelta(seconds=60)
    turn.action_deadline = deadline
    turn.save(update_fields=("action_deadline",))

    assert mark_connected(participant_id=participant.pk, channel_name="channel-a")

    assert mark_reconnecting(
        participant_id=participant.pk,
        channel_name="channel-a",
    )

    assert mark_connected(participant_id=participant.pk, channel_name="channel-b")

    turn.refresh_from_db()
    assert turn.action_deadline == deadline
