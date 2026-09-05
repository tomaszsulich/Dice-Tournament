from dataclasses import FrozenInstanceError

import pytest

from tournaments.domain.dice import (
    SCHOOL_CATEGORIES,
    DiceContext,
    FigureStrikeOffResult,
    InvalidDiceError,
    InvalidRollNumberError,
    PointsResult,
    PokerScoringVariant,
    SchoolSuccessResult,
    ScoreCategory,
    ScoringConfig,
    ScoringContext,
    make_dice,
)
from tournaments.domain.dice import context as context_module


@pytest.mark.unit
@pytest.mark.parametrize("values", [(1, 2, 3, 4), (1, 2, 3, 4, 5, 6)])
def test_make_dice_rejects_wrong_number_of_values(values: tuple[int, ...]) -> None:
    with pytest.raises(InvalidDiceError, match="Exactly 5 dice"):
        make_dice(values)


@pytest.mark.unit
@pytest.mark.parametrize(
    "values",
    [
        (0, 2, 3, 4, 5),
        (1, 2, 3, 4, 7),
        (1, 2, 3, 4, True),
    ],
)
def test_make_dice_rejects_illegal_values(values: tuple[int, ...]) -> None:
    with pytest.raises(InvalidDiceError, match="integer from 1 to 6"):
        make_dice(values)


@pytest.mark.unit
def test_make_dice_returns_immutable_tuple() -> None:
    dice = make_dice([6, 5, 4, 3, 2])

    assert dice == (6, 5, 4, 3, 2)
    assert isinstance(dice, tuple)


@pytest.mark.unit
def test_dice_context_analyzes_snapshot_once(monkeypatch: pytest.MonkeyPatch) -> None:
    original_analyze = context_module._analyze_dice
    calls = 0

    def counting_analyze(dice):
        nonlocal calls
        calls += 1
        return original_analyze(dice)

    monkeypatch.setattr(context_module, "_analyze_dice", counting_analyze)

    context = DiceContext.from_values((4, 2, 4, 1, 6))

    assert context.counts == {1: 1, 2: 1, 4: 2, 6: 1}
    assert context.total == 17
    assert context.unique == frozenset({1, 2, 4, 6})
    assert context.sorted_values == (1, 2, 4, 4, 6)

    _ = context.counts
    _ = context.total
    _ = context.unique
    _ = context.sorted_values

    assert calls == 1


@pytest.mark.unit
def test_dice_context_is_immutable() -> None:
    context = DiceContext.from_values((1, 1, 2, 3, 4))

    with pytest.raises(FrozenInstanceError):
        context.total = 99  # type: ignore[misc]

    with pytest.raises(TypeError):
        context.counts[1] = 99  # type: ignore[index]


@pytest.mark.unit
@pytest.mark.parametrize("roll_number", [1, 2, 3])
def test_scoring_context_accepts_rolls_within_turn_range(
    roll_number: int,
) -> None:
    dice = DiceContext.from_values((1, 2, 3, 4, 5))
    config = ScoringConfig(poker_variant=PokerScoringVariant.A)

    context = ScoringContext(
        dice=dice,
        roll_number=roll_number,
        config=config,
    )

    assert context.roll_number == roll_number


@pytest.mark.unit
@pytest.mark.parametrize("roll_number", [0, 4])
def test_scoring_context_rejects_roll_outside_turn_range(roll_number: int) -> None:
    dice = DiceContext.from_values((1, 2, 3, 4, 5))
    config = ScoringConfig(poker_variant=PokerScoringVariant.A)

    with pytest.raises(InvalidRollNumberError, match="between 1 and 3"):
        ScoringContext(dice=dice, roll_number=roll_number, config=config)


@pytest.mark.unit
def test_scoring_context_and_config_are_immutable() -> None:
    dice = DiceContext.from_values((1, 2, 3, 4, 5))
    config = ScoringConfig(poker_variant=PokerScoringVariant.B)
    context = ScoringContext(dice=dice, roll_number=1, config=config)

    with pytest.raises(FrozenInstanceError):
        context.roll_number = 2  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        config.poker_variant = PokerScoringVariant.A  # type: ignore[misc]


@pytest.mark.unit
def test_score_category_is_closed_and_has_approved_ui_labels() -> None:
    expected = {
        ScoreCategory.ONES: ("ones", "1"),
        ScoreCategory.TWOS: ("twos", "2"),
        ScoreCategory.THREES: ("threes", "3"),
        ScoreCategory.FOURS: ("fours", "4"),
        ScoreCategory.FIVES: ("fives", "5"),
        ScoreCategory.SIXES: ("sixes", "6"),
        ScoreCategory.PAIR: ("pair", "Pair"),
        ScoreCategory.TWO_PAIRS: ("two_pairs", "Two Pairs"),
        ScoreCategory.TRIPLE: ("triple", "Triple"),
        ScoreCategory.QUAD: ("quad", "Quad"),
        ScoreCategory.FULL: ("full", "Full"),
        ScoreCategory.EVEN: ("even", "Even"),
        ScoreCategory.ODD: ("odd", "Odd"),
        ScoreCategory.SMALL_STRAIGHT: ("small_straight", "Small Straight"),
        ScoreCategory.LARGE_STRAIGHT: ("large_straight", "Large Straight"),
        ScoreCategory.GAP: ("gap", "Gap"),
        ScoreCategory.CHANCE: ("chance", "Chance"),
        ScoreCategory.POKER: ("poker", "Poker"),
    }

    assert list(ScoreCategory) == list(expected)
    assert {
        category: (category.value, category.label) for category in ScoreCategory
    } == expected
    assert ScoreCategory.__members__.get("SCHOOL") is None


@pytest.mark.unit
def test_poker_scoring_variants_are_closed_and_stable() -> None:
    assert list(PokerScoringVariant) == [
        PokerScoringVariant.A,
        PokerScoringVariant.B,
    ]
    assert [variant.value for variant in PokerScoringVariant] == ["a", "b"]


@pytest.mark.unit
def test_school_categories_are_exactly_the_six_number_fields() -> None:
    assert SCHOOL_CATEGORIES == frozenset(
        {
            ScoreCategory.ONES,
            ScoreCategory.TWOS,
            ScoreCategory.THREES,
            ScoreCategory.FOURS,
            ScoreCategory.FIVES,
            ScoreCategory.SIXES,
        }
    )


@pytest.mark.unit
def test_scoring_result_variants_are_disjoint_and_immutable() -> None:
    points = PointsResult(points=18)
    school = SchoolSuccessResult(category=ScoreCategory.THREES)
    strike_off = FigureStrikeOffResult()

    assert type(points) is PointsResult
    assert type(school) is SchoolSuccessResult
    assert type(strike_off) is FigureStrikeOffResult
    assert school.category is ScoreCategory.THREES

    with pytest.raises(FrozenInstanceError):
        points.points = 0  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        school.category = ScoreCategory.FOURS  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.parametrize(
    "category",
    [
        ScoreCategory.ONES,
        ScoreCategory.TWOS,
        ScoreCategory.THREES,
        ScoreCategory.FOURS,
        ScoreCategory.FIVES,
        ScoreCategory.SIXES,
    ],
)
def test_school_result_accepts_each_school_category(
    category: ScoreCategory,
) -> None:
    result = SchoolSuccessResult(category=category)

    assert result.category is category


@pytest.mark.unit
def test_school_result_rejects_non_school_category() -> None:
    with pytest.raises(ValueError, match="requires one of the 1-6 school categories"):
        SchoolSuccessResult(category=ScoreCategory.PAIR)
