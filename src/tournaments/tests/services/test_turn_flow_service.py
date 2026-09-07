import importlib

import pytest
from django.utils import timezone

from accounts.tests.factories import PlayerProfileFactory
from tournaments.domain.dice.categories import SCHOOL_CATEGORIES, ScoreCategory
from tournaments.models import (
    GameParticipant,
    IdempotencyRecord,
    Roll,
    ScoreEntry,
    ScoreResultKind,
    TournamentParticipant,
    Turn,
)
from tournaments.services.dice.hold_dice import (
    HoldForbidden,
    HoldUnavailable,
    InvalidHoldPayload,
    set_held_dice,
)
from tournaments.services.dice.roll_dice import execute_roll
from tournaments.services.dice.select_category import (
    BONUS_REQUIRED_CATEGORIES,
    CategoryAlreadyUsed,
    CategoryForbidden,
    CategoryUnavailable,
    InvalidCategorySelection,
    select_category,
)
from tournaments.tests.helpers import FakeRandomizer


def _publisher(events):
    return lambda event, payload: events.append((event, payload))


def _add_second_participant(game):
    profile = PlayerProfileFactory.create()

    participant = TournamentParticipant.objects.create(
        tournament=game.round.tournament,
        player_profile=profile,
        full_name_snapshot="Player Two",
        display_name_snapshot="Player Two",
    )

    game_participant = GameParticipant.objects.create(
        game=game,
        tournament_participant=participant,
        turn_order=2,
    )

    return profile.user, game_participant


def _roll(turn, values=(1, 2, 3, 4, 5), number=1):
    return Roll.objects.create(
        turn=turn,
        roll_number=number,
        **{f"die_{index}": value for index, value in enumerate(values, start=1)},
    )


def test_completion_bonus_requires_chance() -> None:
    assert BONUS_REQUIRED_CATEGORIES == frozenset(ScoreCategory) - SCHOOL_CATEGORIES
    assert ScoreCategory.CHANCE in BONUS_REQUIRED_CATEGORIES


@pytest.mark.django_db
def test_roll_keeps_post_roll_snapshot_while_turn_tracks_later_hold_choice(roll_setup):
    user, game, turn = roll_setup()

    execute_roll(
        user=user,
        game_id=game.pk,
        payload={},
        key="roll-1",
        rng=FakeRandomizer([1, 2, 3, 4, 5]),
        publisher=lambda _event, _payload: None,
    )

    first = turn.rolls.get(roll_number=1)
    assert first.held_after_roll == (False,) * 5

    set_held_dice(
        user=user,
        game_id=game.pk,
        held_flags=(True, False, True, False, False),
        publisher=lambda _event, _payload: None,
    )

    turn.refresh_from_db()
    first.refresh_from_db()

    assert turn.held_dice == (True, False, True, False, False)
    assert first.held_after_roll == (False,) * 5

    execute_roll(
        user=user,
        game_id=game.pk,
        payload={},
        key="roll-2",
        rng=FakeRandomizer([6, 6, 6]),
        publisher=lambda _event, _payload: None,
    )

    second = turn.rolls.get(roll_number=2)

    assert second.values == (1, 6, 3, 6, 6)
    assert second.held_after_roll == (True, False, True, False, False)


@pytest.mark.django_db
def test_hold_requires_exactly_five_real_booleans(roll_setup):
    user, game, turn = roll_setup()

    _roll(turn)

    with pytest.raises(InvalidHoldPayload):
        set_held_dice(
            user=user,
            game_id=game.pk,
            held_flags=(True, False, True, False, 1),
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_hold_is_rejected_before_first_and_after_third_roll(roll_setup):
    user, game, turn = roll_setup()

    with pytest.raises(HoldUnavailable):
        set_held_dice(
            user=user,
            game_id=game.pk,
            held_flags=(False,) * 5,
            publisher=lambda _event, _payload: None,
        )

    for number in range(1, 4):
        _roll(turn, number=number)

    with pytest.raises(HoldUnavailable):
        set_held_dice(
            user=user,
            game_id=game.pk,
            held_flags=(True,) * 5,
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_other_user_cannot_change_active_turn_holds(roll_setup):
    _user, game, turn = roll_setup()
    _roll(turn)
    other = PlayerProfileFactory.create().user

    with pytest.raises(HoldForbidden):
        set_held_dice(
            user=other,
            game_id=game.pk,
            held_flags=(True,) * 5,
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_category_requires_at_least_one_roll(roll_setup):
    user, game, _turn = roll_setup()

    with pytest.raises(CategoryUnavailable):
        select_category(
            user=user,
            game_id=game.pk,
            payload={"category": ScoreCategory.CHANCE},
            key="category-before-roll",
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_other_user_cannot_choose_active_turn_category(roll_setup):
    _user, game, turn = roll_setup()
    _roll(turn)
    other = PlayerProfileFactory.create().user

    with pytest.raises(CategoryForbidden):
        select_category(
            user=other,
            game_id=game.pk,
            payload={"category": ScoreCategory.CHANCE},
            key="foreign-category",
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_category_uses_last_roll_and_first_hand_multiplier(roll_setup):
    user, game, turn = roll_setup()
    _roll(turn, values=(1, 2, 3, 4, 5))

    response = select_category(
        user=user,
        game_id=game.pk,
        payload={"category": ScoreCategory.CHANCE},
        key="chance-first-hand",
        publisher=lambda _event, _payload: None,
    )

    assert response["score_entry"] == {
        "id": ScoreEntry.objects.get().pk,
        "turn_id": turn.pk,
        "category": ScoreCategory.CHANCE,
        "result_kind": ScoreResultKind.POINTS,
        "value": 30,
    }

    participant = turn.game_participant
    participant.refresh_from_db()

    assert participant.figure_points == 30
    assert participant.raw_score == 30
    assert participant.final_score == 30

    turn.refresh_from_db()
    assert turn.completed_at is not None


@pytest.mark.django_db
def test_school_zero_and_figure_strike_off_keep_distinct_persistence(roll_setup):
    user, game, turn = roll_setup()
    _roll(turn, values=(3, 3, 3, 1, 2))

    school = select_category(
        user=user,
        game_id=game.pk,
        payload={"category": ScoreCategory.THREES},
        key="school-zero",
        publisher=lambda _event, _payload: None,
    )

    assert school["score_entry"]["result_kind"] == ScoreResultKind.SCHOOL_BALANCE
    assert school["score_entry"]["value"] == 0

    next_turn = Turn.objects.get(pk=school["next_turn_id"])
    _roll(next_turn, values=(1, 2, 3, 4, 5))

    figure = select_category(
        user=user,
        game_id=game.pk,
        payload={"category": ScoreCategory.POKER},
        key="figure-x",
        publisher=lambda _event, _payload: None,
    )

    assert figure["score_entry"]["result_kind"] == ScoreResultKind.STRIKE_OFF
    assert figure["score_entry"]["value"] is None


@pytest.mark.django_db
def test_category_retry_replays_without_scoring_twice(roll_setup, monkeypatch):
    user, game, turn = roll_setup()
    _roll(turn, values=(1, 2, 3, 4, 5))
    calls = 0

    from tournaments.services.dice import select_category as exported_select

    module = importlib.import_module("tournaments.services.dice.select_category")
    original_score = module.score

    def counting_score(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_score(*args, **kwargs)

    monkeypatch.setattr(module, "score", counting_score)

    kwargs = {
        "user": user,
        "game_id": game.pk,
        "payload": {"category": ScoreCategory.CHANCE},
        "key": "category-retry",
        "publisher": lambda _event, _payload: None,
    }

    first = exported_select(**kwargs)
    second = exported_select(**kwargs)

    assert second == first
    assert calls == 1
    assert ScoreEntry.objects.count() == 1
    assert IdempotencyRecord.objects.filter(command="CHOOSE_CATEGORY").count() == 1


@pytest.mark.django_db
def test_used_category_is_rejected_explicitly(roll_setup):
    user, game, initial_turn = roll_setup()
    participant = initial_turn.game_participant
    initial_turn.delete()

    previous = Turn.objects.create(game_participant=participant, number=1)
    previous.completed_at = timezone.now()
    previous.save(update_fields=["completed_at"])

    ScoreEntry.objects.create(
        turn=previous,
        game_participant=participant,
        category=ScoreCategory.CHANCE,
        result_kind=ScoreResultKind.POINTS,
        value=10,
    )

    current = Turn.objects.create(game_participant=participant, number=2)
    _roll(current)

    with pytest.raises(CategoryAlreadyUsed):
        select_category(
            user=user,
            game_id=game.pk,
            payload={"category": ScoreCategory.CHANCE},
            key="chance-again",
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_pair_subselection_is_passed_to_scoring_strategy(roll_setup):
    user, game, turn = roll_setup()
    _roll(turn, values=(3, 3, 3, 5, 5))

    with pytest.raises(InvalidCategorySelection):
        select_category(
            user=user,
            game_id=game.pk,
            payload={"category": ScoreCategory.PAIR},
            key="ambiguous-pair",
            publisher=lambda _event, _payload: None,
        )

    response = select_category(
        user=user,
        game_id=game.pk,
        payload={"category": ScoreCategory.PAIR, "pair_value": 5},
        key="chosen-pair",
        publisher=lambda _event, _payload: None,
    )

    assert response["score_entry"]["value"] == 20


@pytest.mark.django_db
def test_turn_advances_in_cyclic_turn_order_and_resets_holds(roll_setup):
    user_one, game, turn_one = roll_setup()
    user_two, participant_two = _add_second_participant(game)
    _roll(turn_one)

    first = select_category(
        user=user_one,
        game_id=game.pk,
        payload={"category": ScoreCategory.CHANCE},
        key="p1-chance",
        publisher=lambda _event, _payload: None,
    )

    turn_two = Turn.objects.get(pk=first["next_turn_id"])

    assert turn_two.game_participant == participant_two
    assert turn_two.number == 1
    assert turn_two.held_dice == (False,) * 5

    _roll(turn_two)

    second = select_category(
        user=user_two,
        game_id=game.pk,
        payload={"category": ScoreCategory.CHANCE},
        key="p2-chance",
        publisher=lambda _event, _payload: None,
    )

    next_one = Turn.objects.get(pk=second["next_turn_id"])

    assert next_one.game_participant == turn_one.game_participant
    assert next_one.number == 2


@pytest.mark.django_db
def test_last_category_completes_participant_and_game(roll_setup):
    user, game, active_turn = roll_setup()
    participant = active_turn.game_participant
    active_turn.delete()

    categories = list(ScoreCategory)
    final_category = categories[-1]

    for number, category in enumerate(categories[:-1], start=1):
        turn = Turn.objects.create(game_participant=participant, number=number)
        turn.completed_at = turn.game_participant.tournament_participant.joined_at
        turn.save(update_fields=["completed_at"])
        is_school = category in SCHOOL_CATEGORIES
        is_chance = category is ScoreCategory.CHANCE

        ScoreEntry.objects.create(
            turn=turn,
            game_participant=participant,
            category=category,
            result_kind=(
                ScoreResultKind.SCHOOL_BALANCE
                if is_school
                else ScoreResultKind.POINTS
                if is_chance
                else ScoreResultKind.STRIKE_OFF
            ),
            value=0 if is_school else 5 if is_chance else None,
        )

    final_turn = Turn.objects.create(
        game_participant=participant,
        number=len(categories),
    )

    _roll(final_turn, values=(6, 6, 6, 6, 6))

    response = select_category(
        user=user,
        game_id=game.pk,
        payload={"category": final_category},
        key="last-category",
        publisher=lambda _event, _payload: None,
    )

    participant.refresh_from_db()

    assert participant.is_completed is True
    assert response["game_complete"] is True
    assert response["next_turn_id"] is None


@pytest.mark.django_db
def test_category_rollback_keeps_turn_and_queue_unchanged(roll_setup, monkeypatch):
    user, game, turn = roll_setup()
    _roll(turn)
    events = []

    def fail_create(**_kwargs):
        raise RuntimeError("forced idempotency failure")

    monkeypatch.setattr(IdempotencyRecord.objects, "create", fail_create)

    with pytest.raises(RuntimeError, match="forced idempotency failure"):
        select_category(
            user=user,
            game_id=game.pk,
            payload={"category": ScoreCategory.CHANCE},
            key="rollback-category",
            publisher=_publisher(events),
        )

    turn.refresh_from_db()

    assert turn.completed_at is None
    assert not ScoreEntry.objects.exists()
    assert Turn.objects.count() == 1
    assert events == []
