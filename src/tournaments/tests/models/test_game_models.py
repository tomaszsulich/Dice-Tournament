import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from accounts.models import PlayerProfile
from accounts.tests.factories import UserFactory
from tournaments.domain.dice.categories import ScoreCategory
from tournaments.domain.tournament.types import (
    EventMode,
    PokerScoringVariant,
    TournamentStatus,
)
from tournaments.models import (
    Game,
    GameParticipant,
    Roll,
    Round,
    ScoreEntry,
    ScoreResultKind,
    Tournament,
    TournamentParticipant,
    Turn,
)
from tournaments.serializers import GameSerializer


def build_tournament(name: str = "Dice Game Tournament") -> Tournament:
    return Tournament.objects.create(
        name=name,
        status=TournamentStatus.ACTIVE,
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=5,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )


def build_participant(tournament: Tournament, suffix: str) -> TournamentParticipant:
    user = UserFactory.create(
        username=f"player-{suffix}",
        first_name="Jan",
        last_name=suffix,
    )

    profile = PlayerProfile.objects.create(
        user=user,
        display_name=f"Jan {suffix}",
    )

    return TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot=f"Jan {suffix}",
        display_name_snapshot=f"Jan {suffix}",
    )


@pytest.fixture
def game_setup(db):
    tournament = build_tournament()

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        name="Group round 1",
    )

    participant = build_participant(tournament, "One")

    game = Game.objects.create(
        round=round_,
        display_number=1,
        allocation_seed=20260906,
        allocation_cost=16,
    )

    game_participant = GameParticipant.objects.create(
        game=game,
        tournament_participant=participant,
        turn_order=1,
    )

    turn = Turn.objects.create(
        game_participant=game_participant,
        number=1,
    )

    return tournament, round_, game, game_participant, turn


@pytest.mark.django_db(transaction=True)
def test_games_have_stable_unique_display_numbers_and_serializer_labels():
    tournament = build_tournament()

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        name="Group round 1",
    )

    first = Game.objects.create(
        round=round_,
        display_number=1,
        allocation_seed=11,
        allocation_cost=0,
    )

    other_round = Round.objects.create(
        tournament=tournament,
        number=2,
        name="Group round 2",
    )

    Game.objects.create(
        round=other_round,
        display_number=1,
        allocation_seed=99,
        allocation_cost=0,
    )

    second = Game.objects.create(
        round=round_,
        display_number=2,
        allocation_seed=11,
        allocation_cost=6,
    )

    assert second.pk != second.display_number
    assert GameSerializer(first).data["display_label"] == "Stół #1"
    assert GameSerializer(second).data["display_label"] == "Stół #2"

    with pytest.raises(IntegrityError):
        Game.objects.create(
            round=round_,
            display_number=1,
            allocation_seed=12,
            allocation_cost=10,
        )


@pytest.mark.django_db
def test_game_participant_persists_turn_order_and_score_aggregates(game_setup):
    _tournament, _round_, _game, game_participant, _turn = game_setup

    assert game_participant.turn_order == 1
    assert game_participant.is_completed is False
    assert game_participant.raw_score == 0
    assert game_participant.school_balance == 0
    assert game_participant.figure_points == 0
    assert game_participant.bonus_points == 0
    assert game_participant.final_score == 0


@pytest.mark.django_db
def test_partial_reroll_stores_complete_snapshot_with_post_roll_holds(game_setup):
    _tournament, _round_, _game, _game_participant, turn = game_setup

    Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=2,
        die_2=2,
        die_3=4,
        die_4=5,
        die_5=6,
    )

    second = Roll.objects.create(
        turn=turn,
        roll_number=2,
        die_1=2,
        die_2=2,
        die_3=4,
        die_4=4,
        die_5=6,
        held_die_1=True,
        held_die_2=True,
        held_die_3=False,
        held_die_4=False,
        held_die_5=True,
    )

    assert second.values == (2, 2, 4, 4, 6)
    assert second.held_after_roll == (True, True, False, False, True)


@pytest.mark.django_db(transaction=True)
def test_fourth_roll_is_rejected_by_database(game_setup):
    _tournament, _round_, _game, _game_participant, turn = game_setup

    with pytest.raises(IntegrityError):
        Roll.objects.create(
            turn=turn,
            roll_number=4,
            die_1=1,
            die_2=2,
            die_3=3,
            die_4=4,
            die_5=5,
        )


@pytest.mark.django_db(transaction=True)
def test_die_value_outside_one_to_six_is_rejected_by_database(game_setup):
    _tournament, _round_, _game, _game_participant, turn = game_setup

    with pytest.raises(IntegrityError):
        Roll.objects.create(
            turn=turn,
            roll_number=1,
            die_1=0,
            die_2=2,
            die_3=3,
            die_4=4,
            die_5=5,
        )


@pytest.mark.django_db(transaction=True)
def test_first_roll_cannot_claim_preexisting_held_dice(game_setup):
    _tournament, _round_, _game, _game_participant, turn = game_setup

    with pytest.raises(IntegrityError):
        Roll.objects.create(
            turn=turn,
            roll_number=1,
            die_1=1,
            die_2=2,
            die_3=3,
            die_4=4,
            die_5=5,
            held_die_1=True,
        )


@pytest.mark.django_db(transaction=True)
def test_roll_number_is_unique_within_turn(game_setup):
    _tournament, _round_, _game, _game_participant, turn = game_setup

    values = {
        "die_1": 1,
        "die_2": 2,
        "die_3": 3,
        "die_4": 4,
        "die_5": 5,
    }

    Roll.objects.create(turn=turn, roll_number=1, **values)

    with pytest.raises(IntegrityError):
        Roll.objects.create(turn=turn, roll_number=1, **values)


@pytest.mark.django_db
def test_accepted_roll_snapshot_cannot_be_modified(game_setup):
    _tournament, _round_, _game, _game_participant, turn = game_setup

    roll = Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    roll.die_1 = 6

    with pytest.raises(ValidationError, match="cannot be modified"):
        roll.save()


@pytest.mark.django_db(transaction=True)
def test_category_can_be_used_only_once_per_game_participant(game_setup):
    _tournament, _round_, _game, game_participant, first_turn = game_setup

    second_turn = Turn.objects.create(
        game_participant=game_participant,
        number=2,
    )

    ScoreEntry.objects.create(
        turn=first_turn,
        game_participant=game_participant,
        category=ScoreCategory.CHANCE,
        result_kind=ScoreResultKind.POINTS,
        value=18,
    )

    with pytest.raises(IntegrityError):
        ScoreEntry.objects.create(
            turn=second_turn,
            game_participant=game_participant,
            category=ScoreCategory.CHANCE,
            result_kind=ScoreResultKind.POINTS,
            value=21,
        )


@pytest.mark.django_db(transaction=True)
def test_turn_accepts_exactly_one_score_entry(game_setup):
    _tournament, _round_, _game, game_participant, turn = game_setup

    ScoreEntry.objects.create(
        turn=turn,
        game_participant=game_participant,
        category=ScoreCategory.PAIR,
        result_kind=ScoreResultKind.POINTS,
        value=10,
    )

    with pytest.raises(IntegrityError):
        ScoreEntry.objects.create(
            turn=turn,
            game_participant=game_participant,
            category=ScoreCategory.TRIPLE,
            result_kind=ScoreResultKind.POINTS,
            value=15,
        )


@pytest.mark.django_db
def test_score_entry_preserves_school_zero_as_numeric_balance(game_setup):
    _tournament, _round_, _game, game_participant, turn = game_setup

    entry = ScoreEntry(
        turn=turn,
        game_participant=game_participant,
        category=ScoreCategory.THREES,
        result_kind=ScoreResultKind.SCHOOL_BALANCE,
        value=0,
    )

    entry.full_clean()
    entry.save()

    assert entry.value == 0
    assert entry.result_kind == ScoreResultKind.SCHOOL_BALANCE


@pytest.mark.django_db
def test_score_entry_preserves_figure_strike_off_without_numeric_zero(game_setup):
    _tournament, _round_, _game, game_participant, turn = game_setup

    entry = ScoreEntry(
        turn=turn,
        game_participant=game_participant,
        category=ScoreCategory.FULL,
        result_kind=ScoreResultKind.STRIKE_OFF,
        value=None,
    )

    entry.full_clean()
    entry.save()

    assert entry.value is None
    assert entry.result_kind == ScoreResultKind.STRIKE_OFF
