import pytest
from django.core.exceptions import ValidationError

from accounts.tests.factories import PlayerProfileFactory
from tournaments.domain.tournament.rounds import RoundStatus, RoundType
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentParticipant
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
        min_participants=2,
        max_participants=32,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=2,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )


def register_players(
    tournament: Tournament,
    count: int = 2,
) -> list[TournamentParticipant]:
    participants = []

    for index in range(count):
        profile = PlayerProfileFactory.create()

        participants.append(
            TournamentParticipant.objects.create(
                tournament=tournament,
                player_profile=profile,
                full_name_snapshot=f"Player {index + 1}",
                display_name_snapshot=f"Player {index + 1}",
                starting_number=index + 1,
            )
        )

    return participants


def test_open_registration_changes_draft_to_registration(tournament):
    result = open_registration(tournament)
    assert result.status == TournamentStatus.REGISTRATION


def test_open_registration_rejects_non_draft_tournament(tournament):
    tournament.status = TournamentStatus.REGISTRATION
    tournament.save(update_fields=("status",))

    with pytest.raises(ValidationError):
        open_registration(tournament)


def test_start_tournament_activates_players_and_creates_first_round(tournament):
    tournament.status = TournamentStatus.REGISTRATION
    tournament.save(update_fields=("status",))
    participants = register_players(tournament)

    result = start_tournament(tournament)

    assert result.status == TournamentStatus.ACTIVE
    assert result.starts_at is not None
    assert result.registration_closed_at is not None

    for participant in participants:
        participant.refresh_from_db()
        assert participant.status == ParticipantStatus.ACTIVE

    first_round = result.rounds.get()

    assert first_round.number == 1
    assert first_round.type == RoundType.GROUP
    assert first_round.status == RoundStatus.ACTIVE
    assert first_round.started_at is not None
    assert first_round.games.count() == 1

    first_game = first_round.games.get()
    first_turn = first_game.game_participants.get(turn_order=1).turns.get(number=1)

    assert first_turn.completed_at is None


def test_start_tournament_rejects_too_few_players(tournament):
    tournament.status = TournamentStatus.REGISTRATION
    tournament.save(update_fields=("status",))

    register_players(tournament, count=1)

    with pytest.raises(ValidationError):
        start_tournament(tournament)


def test_start_tournament_rejects_too_many_players(tournament):
    tournament.status = TournamentStatus.REGISTRATION
    tournament.max_participants = 2
    tournament.save(update_fields=("status", "max_participants"))

    register_players(tournament, count=3)

    with pytest.raises(ValidationError):
        start_tournament(tournament)


@pytest.mark.parametrize(
    "status",
    [TournamentStatus.DRAFT, TournamentStatus.ACTIVE, TournamentStatus.COMPLETED],
)
def test_start_tournament_rejects_invalid_status(tournament, status):
    tournament.status = status
    tournament.save(update_fields=("status",))

    with pytest.raises(ValidationError):
        start_tournament(tournament)


def test_complete_tournament_rejects_unfinished_round(tournament):
    tournament.status = TournamentStatus.ACTIVE
    tournament.save(update_fields=("status",))

    tournament.rounds.create(
        number=1,
        name="Round 1",
        status=RoundStatus.ACTIVE,
    )

    with pytest.raises(ValidationError):
        complete_tournament(tournament)


def test_complete_tournament_requires_all_configured_group_rounds(tournament):
    tournament.status = TournamentStatus.ACTIVE
    tournament.save(update_fields=("status",))

    tournament.rounds.create(
        number=1,
        name="Round 1",
        type=RoundType.GROUP,
        status=RoundStatus.COMPLETED,
    )

    with pytest.raises(ValidationError):
        complete_tournament(tournament)


def test_complete_tournament_changes_active_to_completed(tournament):
    tournament.status = TournamentStatus.ACTIVE
    tournament.save(update_fields=("status",))

    for number in (1, 2):
        tournament.rounds.create(
            number=number,
            name=f"Round {number}",
            type=RoundType.GROUP,
            status=RoundStatus.COMPLETED,
        )

    result = complete_tournament(tournament)

    assert result.status == TournamentStatus.COMPLETED
    assert result.completed_at is not None


@pytest.mark.parametrize(
    "status",
    [TournamentStatus.DRAFT, TournamentStatus.REGISTRATION, TournamentStatus.COMPLETED],
)
def test_complete_tournament_rejects_invalid_status(tournament, status):
    tournament.status = status
    tournament.save(update_fields=("status",))

    with pytest.raises(ValidationError):
        complete_tournament(tournament)


def test_start_tournament_rejects_count_that_cannot_form_a_table(tournament):
    tournament.status = TournamentStatus.REGISTRATION
    tournament.min_participants = 1
    tournament.save(update_fields=("status", "min_participants"))

    register_players(tournament, count=1)

    with pytest.raises(ValidationError, match="valid table structure"):
        start_tournament(tournament)
