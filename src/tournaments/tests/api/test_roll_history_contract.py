import pytest
from django.http import Http404

from accounts.factories import PlayerProfileFactory, UserFactory
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
    Roll,
    Round,
    Tournament,
    TournamentOrganizer,
    TournamentParticipant,
    Turn,
)
from tournaments.selectors.participant_comparison import (
    get_participant_history_page,
)

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


@pytest.fixture
def roll_history_setup(db):
    organizer = UserFactory.create()
    profile = PlayerProfileFactory.create()

    tournament = Tournament.objects.create(
        name="Completed Cup",
        status=TournamentStatus.COMPLETED,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
        max_participants=4,
        timezone="Europe/Warsaw",
        group_rounds=1,
        table_size=2,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.REMOTE,
    )

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    participation = TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="History Player",
        display_name_snapshot="History Player",
    )

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        name="Round 1",
        status=RoundStatus.COMPLETED,
    )

    game = Game.objects.create(
        round=round_,
        display_number=1,
        allocation_seed=1,
        allocation_cost=0,
    )

    game_participant = GameParticipant.objects.create(
        game=game,
        tournament_participant=participation,
        turn_order=1,
        is_completed=True,
    )

    turn = Turn.objects.create(game_participant=game_participant, number=1)

    roll = Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    return organizer, profile, tournament, roll


def test_history_distinguishes_holds_used_for_a_roll(roll_history_setup):
    organizer, profile, tournament, roll = roll_history_setup

    result = get_participant_history_page(
        actor=organizer,
        participant_id=profile.pk,
        tournament_id=tournament.pk,
        page_number=1,
    )

    assert result["items"][0]["id"] == roll.pk
    assert result["items"][0]["held_for_roll"] == [False] * 5


def test_participant_can_read_only_their_own_completed_history(roll_history_setup):
    _organizer, profile, tournament, roll = roll_history_setup

    result = get_participant_history_page(
        actor=profile.user,
        participant_id=profile.pk,
        tournament_id=tournament.pk,
        page_number=1,
    )

    assert [item["id"] for item in result["items"]] == [roll.pk]

    with pytest.raises(Http404):
        get_participant_history_page(
            actor=PlayerProfileFactory.create().user,
            participant_id=profile.pk,
            tournament_id=tournament.pk,
            page_number=1,
        )
