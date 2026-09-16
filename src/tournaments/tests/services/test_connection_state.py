from datetime import timedelta

import pytest
from django.utils import timezone

from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantConnectionStatus,
    ParticipantStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import (
    Game,
    GameParticipant,
    Round,
    Tournament,
    TournamentParticipant,
)
from tournaments.services.connection_state import (
    RECONNECT_GRACE,
    active_game_for_user,
    assignment_context_for_user,
    decision_deadline_for,
    mark_connected,
    mark_reconnecting,
    official_game_for_participant,
    refresh_connection_status,
)

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


def _add_active_assignment(user, number: int) -> tuple[TournamentParticipant, Game]:
    tournament = Tournament.objects.create(
        name=f"Connection Tournament {number}",
        status=TournamentStatus.ACTIVE,
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
        player_profile=user.player_profile,
        full_name_snapshot="Player One",
        display_name_snapshot="Player One",
        status=ParticipantStatus.ACTIVE,
    )

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        status=RoundStatus.ACTIVE,
    )

    game = Game.objects.create(
        round=round_,
        display_number=1,
        allocation_seed=number,
        allocation_cost=0,
    )

    GameParticipant.objects.create(
        game=game,
        tournament_participant=participant,
        turn_order=1,
    )

    return participant, game


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
def test_active_game_lookup_query_count_is_independent_of_participation_count(
    roll_setup,
    django_assert_num_queries,
):
    user, first_game, _turn = roll_setup()

    for number in range(2, 6):
        _add_active_assignment(user, number)

    with django_assert_num_queries(1):
        game = active_game_for_user(user.pk)

    assert game == first_game


@pytest.mark.django_db
def test_assignment_context_query_count_is_independent_of_participation_count(
    roll_setup,
    django_assert_num_queries,
):
    user, first_game, _turn = roll_setup()
    first_participant = first_game.game_participants.get().tournament_participant
    expected = [(first_participant.pk, first_game.pk)]

    for number in range(2, 6):
        participant, game = _add_active_assignment(user, number)
        expected.append((participant.pk, game.pk))

    with django_assert_num_queries(2):
        participant_ids, assignments = assignment_context_for_user(user.pk)

    assert participant_ids == [participant_id for participant_id, _game_id in expected]
    assert assignments == [(game_id, 0) for _participant_id, game_id in expected]


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
