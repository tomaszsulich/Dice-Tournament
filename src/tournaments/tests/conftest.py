import pytest

from accounts.tests.factories import PlayerProfileFactory
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
    TournamentParticipant,
    Turn,
)


@pytest.fixture
def roll_setup(db):
    def build(mode=EventMode.REMOTE):
        profile = PlayerProfileFactory.create()

        tournament = Tournament.objects.create(
            name="Roll Tournament",
            status=TournamentStatus.ACTIVE,
            registration_mode=RegistrationMode.ORGANIZER_ONLY,
            min_participants=1,
            max_participants=4,
            timezone="Europe/Warsaw",
            group_rounds=2,
            table_size=2,
            poker_scoring_variant=PokerScoringVariant.A,
            event_mode=mode,
        )

        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            player_profile=profile,
            full_name_snapshot="Player One",
            display_name_snapshot="Player One",
        )

        round_ = Round.objects.create(tournament=tournament, number=1)

        game = Game.objects.create(
            round=round_,
            display_number=1,
            allocation_seed=1,
            allocation_cost=0,
        )

        game_participant = GameParticipant.objects.create(
            game=game,
            tournament_participant=participant,
            turn_order=1,
        )

        turn = Turn.objects.create(game_participant=game_participant, number=1)
        return profile.user, game, turn

    return build
