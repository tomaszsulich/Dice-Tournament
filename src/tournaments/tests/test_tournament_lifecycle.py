import pytest
from django.core.exceptions import ValidationError

from tournaments.domain.tournament.types import (
    EventMode,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament
from tournaments.services.tournament_lifecycle import (
    complete_tournament,
    open_registration,
    start_tournament,
)


@pytest.fixture
def tournament(db):
    return Tournament.objects.create(
        name="Lifecycle Tournament",
        status=TournamentStatus.DRAFT,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=8,
        max_participants=32,
        timezone="Europe/Warsaw",
        group_rounds=5,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )


def test_open_registration_changes_draft_to_registration(tournament):
    open_registration(tournament)
    assert tournament.status == TournamentStatus.REGISTRATION


def test_open_registration_rejects_non_draft_tournament(tournament):
    tournament.status = TournamentStatus.REGISTRATION
    tournament.save(update_fields=("status",))

    with pytest.raises(ValidationError):
        open_registration(tournament)


def test_start_tournament_changes_registration_to_active(tournament):
    tournament.status = TournamentStatus.REGISTRATION
    tournament.save(update_fields=("status",))

    start_tournament(tournament)

    assert tournament.status == TournamentStatus.ACTIVE
    assert tournament.starts_at is not None


@pytest.mark.parametrize(
    "status",
    [
        TournamentStatus.DRAFT,
        TournamentStatus.ACTIVE,
        TournamentStatus.COMPLETED,
    ],
)
def test_start_tournament_rejects_invalid_status(tournament, status):
    tournament.status = status
    tournament.save(update_fields=("status",))

    with pytest.raises(ValidationError):
        start_tournament(tournament)


def test_complete_tournament_changes_active_to_completed(tournament):
    tournament.status = TournamentStatus.ACTIVE
    tournament.save(update_fields=("status",))

    complete_tournament(tournament)

    assert tournament.status == TournamentStatus.COMPLETED
    assert tournament.completed_at is not None


@pytest.mark.parametrize(
    "status",
    [
        TournamentStatus.DRAFT,
        TournamentStatus.REGISTRATION,
        TournamentStatus.COMPLETED,
    ],
)
def test_complete_tournament_rejects_invalid_status(tournament, status):
    tournament.status = status
    tournament.save(update_fields=("status",))

    with pytest.raises(ValidationError):
        complete_tournament(tournament)
