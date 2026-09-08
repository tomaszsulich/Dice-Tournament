from concurrent.futures import ThreadPoolExecutor
from threading import Barrier as ThreadBarrier

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections

from accounts.tests.factories import PlayerProfileFactory
from tournaments.domain.tournament.rounds import RoundStatus, RoundType
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import (
    Game,
    GameParticipant,
    Round,
    TieBreakDecision,
    Tournament,
    TournamentOrganizer,
    TournamentParticipant,
)
from tournaments.services.round_barrier import BarrierResult, evaluate_round_barrier

type ActiveTournament = tuple[Tournament, list[TournamentParticipant]]


@pytest.fixture
def active_tournament(db):
    tournament = Tournament.objects.create(
        name="Barrier Tournament",
        status=TournamentStatus.ACTIVE,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
        max_participants=8,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=3,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )

    participants = []

    for index in range(3):
        profile = PlayerProfileFactory.create()

        participants.append(
            TournamentParticipant.objects.create(
                tournament=tournament,
                player_profile=profile,
                full_name_snapshot=f"Player {index + 1}",
                display_name_snapshot=f"Player {index + 1}",
                status=ParticipantStatus.ACTIVE,
            )
        )

    return tournament, participants


def add_round(
    tournament: Tournament,
    participants: list[TournamentParticipant],
    number: int,
    scores: tuple[int, ...],
    *,
    completed: bool = True,
    round_type: str = RoundType.GROUP,
) -> Round:
    """Create one-table round data needed by barrier integration tests."""
    round_ = Round.objects.create(
        tournament=tournament,
        number=number,
        name=f"Round {number}",
        type=round_type,
        status=RoundStatus.ACTIVE,
    )

    game = Game.objects.create(
        round=round_,
        display_number=1,
        allocation_seed=number,
        allocation_cost=0,
    )

    for turn_order, (participant, score) in enumerate(
        zip(participants, scores, strict=True),
        start=1,
    ):
        GameParticipant.objects.create(
            game=game,
            tournament_participant=participant,
            turn_order=turn_order,
            is_completed=completed,
            raw_score=score,
        )

    return round_


def test_empty_round_keeps_barrier_waiting(active_tournament):
    tournament, _participants = active_tournament

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        name="Round 1",
        status=RoundStatus.ACTIVE,
    )

    result = evaluate_round_barrier(
        round_id=round_.pk,
        publisher=lambda _event, _payload: None,
    )

    assert result.state == "waiting"
    assert tournament.rounds.count() == 1


def test_incomplete_round_keeps_barrier_waiting(active_tournament):
    tournament, participants = active_tournament
    round_ = add_round(tournament, participants, 1, (10, 9, 8), completed=False)

    result = evaluate_round_barrier(
        round_id=round_.pk,
        publisher=lambda _event, _payload: None,
    )

    assert result.state == "waiting"
    assert tournament.rounds.count() == 1


def test_completed_nonfinal_round_creates_exactly_one_next_round(active_tournament):
    tournament, participants = active_tournament
    round_ = add_round(tournament, participants, 1, (10, 9, 8))

    first = evaluate_round_barrier(
        round_id=round_.pk,
        publisher=lambda _event, _payload: None,
    )

    second = evaluate_round_barrier(
        round_id=round_.pk,
        publisher=lambda _event, _payload: None,
    )

    assert first.state == "created"
    assert second.state == "existing"
    assert first.round_id == second.round_id
    assert tournament.rounds.filter(number=2).count() == 1


def test_final_material_tie_creates_overtime_for_tied_players_only(active_tournament):
    tournament, participants = active_tournament
    first = add_round(tournament, participants, 1, (10, 20, 5))
    first.status = RoundStatus.COMPLETED
    first.save(update_fields=("status",))
    final = add_round(tournament, participants, 2, (20, 10, 5))

    result = evaluate_round_barrier(
        round_id=final.pk,
        publisher=lambda _event, _payload: None,
    )

    assert result.state == "overtime_created"
    assert set(result.tied_participant_ids) == {participants[0].pk, participants[1].pk}

    overtime = Round.objects.get(pk=result.round_id)
    overtime_ids = set(
        overtime.games.values_list(
            "game_participants__tournament_participant_id",
            flat=True,
        )
    )

    assert overtime.type == RoundType.OVERTIME
    assert overtime_ids == set(result.tied_participant_ids)


def test_repeated_overtime_keeps_only_still_tied_players(active_tournament):
    tournament, participants = active_tournament

    first = add_round(tournament, participants, 1, (10, 20, 5))
    first.status = RoundStatus.COMPLETED
    first.save(update_fields=("status",))

    final = add_round(tournament, participants, 2, (20, 10, 5))

    first_overtime_result = evaluate_round_barrier(
        round_id=final.pk,
        publisher=lambda _event, _payload: None,
    )

    first_overtime = Round.objects.get(pk=first_overtime_result.round_id)

    first_overtime_games = list(first_overtime.games.all())
    assert len(first_overtime_games) == 1

    tied_ids = set(first_overtime_result.tied_participant_ids)

    for game_participant in first_overtime_games[0].game_participants.all():
        assert game_participant.tournament_participant_id in tied_ids
        game_participant.is_completed = True
        game_participant.raw_score = 15
        game_participant.save(update_fields=("is_completed", "raw_score"))

    second_overtime_result = evaluate_round_barrier(
        round_id=first_overtime.pk,
        publisher=lambda _event, _payload: None,
    )

    second_overtime = Round.objects.get(pk=second_overtime_result.round_id)

    second_overtime_ids = set(
        second_overtime.games.values_list(
            "game_participants__tournament_participant_id",
            flat=True,
        )
    )

    assert second_overtime_result.state == "overtime_created"
    assert second_overtime_ids == tied_ids
    assert participants[2].pk not in second_overtime_ids


def test_final_round_without_material_tie_is_tournament_ready(active_tournament):
    tournament, participants = active_tournament

    first = add_round(tournament, participants, 1, (10, 8, 5))
    first.status = RoundStatus.COMPLETED
    first.save(update_fields=("status",))

    final = add_round(tournament, participants, 2, (20, 10, 5))

    result = evaluate_round_barrier(
        round_id=final.pk,
        publisher=lambda _event, _payload: None,
    )

    assert result.state == "tournament_ready"
    assert tournament.rounds.count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_barrier_calls_create_one_next_round():
    """Two workers crossing the barrier together must not create two round #2 rows."""
    tournament = Tournament.objects.create(
        name="Concurrent Barrier",
        status=TournamentStatus.ACTIVE,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
        max_participants=4,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=2,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )

    participants = []

    for index in range(2):
        profile = PlayerProfileFactory.create()

        participants.append(
            TournamentParticipant.objects.create(
                tournament=tournament,
                player_profile=profile,
                full_name_snapshot=f"Concurrent {index + 1}",
                display_name_snapshot=f"Concurrent {index + 1}",
                status=ParticipantStatus.ACTIVE,
            )
        )

    round_ = add_round(tournament, participants, 1, (10, 9))
    gate = ThreadBarrier(2)

    def worker() -> BarrierResult:
        close_old_connections()
        gate.wait()

        try:
            return evaluate_round_barrier(
                round_id=round_.pk,
                publisher=lambda _event, _payload: None,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: worker(), range(2)))

    assert {result.state for result in results} == {"created", "existing"}
    assert tournament.rounds.filter(number=2).count() == 1


def test_organizer_draw_is_durable_when_overtime_is_declared_impossible(
    active_tournament,
):
    tournament, participants = active_tournament
    organizer = PlayerProfileFactory.create().user

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    first = add_round(tournament, participants, 1, (10, 20, 5))
    first.status = RoundStatus.COMPLETED
    first.save(update_fields=("status",))

    final = add_round(tournament, participants, 2, (20, 10, 5))

    result = evaluate_round_barrier(
        round_id=final.pk,
        publisher=lambda _event, _payload: None,
        organizer=organizer,
        draw_reason="  Further overtime cannot be conducted.  ",
        force_draw=True,
    )

    decision = TieBreakDecision.objects.get()

    assert result.state == "drawn"
    assert decision.selected_participant_id in decision.candidate_participant_ids

    assert set(decision.candidate_participant_ids) == {
        participants[0].pk,
        participants[1].pk,
    }

    assert decision.reason == "Further overtime cannot be conducted."


def test_draw_requires_tournament_organizer(active_tournament):
    tournament, participants = active_tournament
    outsider = PlayerProfileFactory.create().user

    first = add_round(tournament, participants, 1, (10, 20, 5))
    first.status = RoundStatus.COMPLETED
    first.save(update_fields=("status",))

    final = add_round(tournament, participants, 2, (20, 10, 5))

    with pytest.raises(PermissionDenied):
        evaluate_round_barrier(
            round_id=final.pk,
            publisher=lambda _event, _payload: None,
            organizer=outsider,
            draw_reason="Overtime is impossible.",
            force_draw=True,
        )

    assert not TieBreakDecision.objects.exists()


def test_draw_requires_nonblank_reason(active_tournament):
    tournament, participants = active_tournament
    organizer = PlayerProfileFactory.create().user

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    first = add_round(tournament, participants, 1, (10, 20, 5))
    first.status = RoundStatus.COMPLETED
    first.save(update_fields=("status",))

    final = add_round(tournament, participants, 2, (20, 10, 5))

    with pytest.raises(ValidationError):
        evaluate_round_barrier(
            round_id=final.pk,
            publisher=lambda _event, _payload: None,
            organizer=organizer,
            draw_reason="   ",
            force_draw=True,
        )

    assert not TieBreakDecision.objects.exists()
