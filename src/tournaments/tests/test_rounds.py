import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from tournaments.domain.tournament.rounds import (
    RoundStatus,
    RoundType,
    can_transition_round_status,
)
from tournaments.domain.tournament.types import (
    EventMode,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Round, Tournament
from tournaments.services.rounds import (
    cancel_round,
    complete_round,
    start_round,
)


@pytest.fixture
def tournament(db):
    return Tournament.objects.create(
        name="Round Tournament",
        status=TournamentStatus.ACTIVE,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=8,
        max_participants=32,
        timezone="Europe/Warsaw",
        group_rounds=5,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )


@pytest.fixture
def round_(tournament):
    return Round.objects.create(
        tournament=tournament,
        number=1,
        name="Group round 1",
    )


def test_round_belongs_directly_to_tournament(round_, tournament):
    assert round_.tournament == tournament
    assert list(tournament.rounds.all()) == [round_]


def test_round_defaults_to_group_type_and_waiting_status(round_):
    assert round_.type == RoundType.GROUP
    assert round_.status == RoundStatus.WAITING


@pytest.mark.django_db(transaction=True)
def test_round_number_must_be_unique_within_tournament(tournament):
    Round.objects.create(
        tournament=tournament,
        number=1,
        name="Group round 1",
    )

    with pytest.raises(IntegrityError):
        Round.objects.create(
            tournament=tournament,
            number=1,
            name="Another round",
        )


@pytest.mark.django_db
def test_same_round_number_is_allowed_in_different_tournaments():
    first_tournament = Tournament.objects.create(
        name="First Tournament",
        status=TournamentStatus.ACTIVE,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=8,
        max_participants=32,
        timezone="Europe/Warsaw",
        group_rounds=5,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )

    second_tournament = Tournament.objects.create(
        name="Second Tournament",
        status=TournamentStatus.ACTIVE,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=8,
        max_participants=32,
        timezone="Europe/Warsaw",
        group_rounds=5,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )

    first_round = Round.objects.create(
        tournament=first_tournament,
        number=1,
        name="Group round 1",
    )

    second_round = Round.objects.create(
        tournament=second_tournament,
        number=1,
        name="Group round 1",
    )

    assert first_round.number == second_round.number


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (RoundStatus.WAITING, RoundStatus.ACTIVE),
        (RoundStatus.WAITING, RoundStatus.CANCELLED),
        (RoundStatus.ACTIVE, RoundStatus.COMPLETED),
        (RoundStatus.ACTIVE, RoundStatus.CANCELLED),
    ],
)
def test_round_domain_allows_supported_transitions(
    current_status,
    target_status,
):
    assert can_transition_round_status(current_status, target_status)


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (RoundStatus.WAITING, RoundStatus.COMPLETED),
        (RoundStatus.ACTIVE, RoundStatus.WAITING),
        (RoundStatus.COMPLETED, RoundStatus.ACTIVE),
        (RoundStatus.COMPLETED, RoundStatus.CANCELLED),
        (RoundStatus.CANCELLED, RoundStatus.WAITING),
        (RoundStatus.CANCELLED, RoundStatus.ACTIVE),
    ],
)
def test_round_domain_rejects_unsupported_transitions(
    current_status,
    target_status,
):
    assert not can_transition_round_status(current_status, target_status)


def test_start_round_changes_waiting_to_active(round_):
    start_round(round_)

    assert round_.status == RoundStatus.ACTIVE
    assert round_.started_at is not None
    assert round_.ended_at is None


def test_complete_round_changes_active_to_completed(round_):
    start_round(round_)

    complete_round(round_)

    assert round_.status == RoundStatus.COMPLETED
    assert round_.started_at is not None
    assert round_.ended_at is not None


@pytest.mark.parametrize(
    "initial_status",
    [
        RoundStatus.WAITING,
        RoundStatus.ACTIVE,
    ],
)
def test_cancel_round_cancels_supported_statuses(round_, initial_status):
    if initial_status == RoundStatus.ACTIVE:
        start_round(round_)

    cancel_round(round_)

    assert round_.status == RoundStatus.CANCELLED
    assert round_.ended_at is not None


def test_start_round_rejects_non_waiting_round(round_):
    start_round(round_)

    with pytest.raises(ValidationError):
        start_round(round_)


def test_complete_round_rejects_waiting_round(round_):
    with pytest.raises(ValidationError):
        complete_round(round_)


def test_complete_round_is_terminal(round_):
    start_round(round_)
    complete_round(round_)

    with pytest.raises(ValidationError):
        cancel_round(round_)


def test_cancelled_round_is_terminal(round_):
    cancel_round(round_)

    with pytest.raises(ValidationError):
        start_round(round_)
