from itertools import product

import pytest

from tournaments.domain.dice import (
    DiceContext,
    FigureStrikeOffResult,
    PointsResult,
    PokerScoringVariant,
    SchoolSuccessResult,
    ScoreCategory,
    ScoringConfig,
    ScoringContext,
)
from tournaments.domain.dice.scoring import (
    REGISTRY,
    AmbiguousFigureSelectionError,
    InvalidFigureSelectionError,
    InvalidScoreSelectionError,
    UnknownScoreCategory,
    apply_school_penalty,
    figure_completion_bonus,
    score,
)


def make_context(
    dice: tuple[int, int, int, int, int],
    *,
    roll_number: int = 2,
    poker_variant: PokerScoringVariant = PokerScoringVariant.A,
):
    return ScoringContext(
        dice=DiceContext.from_values(dice),
        roll_number=roll_number,
        config=ScoringConfig(poker_variant=poker_variant),
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("school_field", "matching_dice"),
    list(
        product(
            [
                (ScoreCategory.ONES, 1),
                (ScoreCategory.TWOS, 2),
                (ScoreCategory.THREES, 3),
                (ScoreCategory.FOURS, 4),
                (ScoreCategory.FIVES, 5),
                (ScoreCategory.SIXES, 6),
            ],
            range(6),
        ),
    ),
)
def test_school_fields_score_balance_from_zero_to_five_matching_dice(
    school_field: tuple[ScoreCategory, int],
    matching_dice: int,
) -> None:
    category, face = school_field
    filler = 2 if face != 2 else 1
    dice = tuple([face] * matching_dice + [filler] * (5 - matching_dice))

    result = score(category, make_context(dice))

    assert result == SchoolSuccessResult(
        category=category,
        balance=(matching_dice - 3) * face,
    )


@pytest.mark.unit
@pytest.mark.parametrize("roll_number", [1, 2, 3])
def test_school_field_never_receives_first_roll_multiplier(roll_number: int) -> None:
    context = make_context((6, 6, 6, 6, 1), roll_number=roll_number)

    result = score(ScoreCategory.SIXES, context)

    assert result == SchoolSuccessResult(category=ScoreCategory.SIXES, balance=6)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("category", "dice", "points"),
    [
        (ScoreCategory.PAIR, (6, 6, 2, 3, 4), 12),
        (ScoreCategory.TWO_PAIRS, (6, 6, 4, 4, 1), 20),
        (ScoreCategory.TRIPLE, (5, 5, 5, 2, 3), 15),
        (ScoreCategory.QUAD, (4, 4, 4, 4, 2), 16),
        (ScoreCategory.FULL, (3, 3, 3, 5, 5), 19),
        (ScoreCategory.EVEN, (2, 2, 4, 4, 6), 18),
        (ScoreCategory.ODD, (1, 1, 3, 5, 5), 15),
        (ScoreCategory.SMALL_STRAIGHT, (5, 1, 4, 2, 3), 15),
        (ScoreCategory.LARGE_STRAIGHT, (6, 3, 2, 5, 4), 20),
        (ScoreCategory.GAP, (1, 2, 3, 4, 6), 16),
        (ScoreCategory.CHANCE, (1, 2, 2, 5, 6), 16),
    ],
)
def test_figure_strategies_score_valid_hands(
    category: ScoreCategory,
    dice: tuple[int, int, int, int, int],
    points: int,
) -> None:
    result = score(category, make_context(dice))
    assert result == PointsResult(points=points)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("dice", "points"),
    [
        ((4, 4, 4, 4, 1), 16),
        ((6, 6, 6, 6, 6), 24),
    ],
)
def test_two_pairs_can_be_formed_from_repeated_same_value(
    dice: tuple[int, int, int, int, int],
    points: int,
) -> None:
    assert score(ScoreCategory.TWO_PAIRS, make_context(dice)) == PointsResult(
        points=points
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("category", "dice"),
    [
        (ScoreCategory.PAIR, (1, 2, 3, 4, 5)),
        (ScoreCategory.TWO_PAIRS, (6, 6, 2, 3, 4)),
        (ScoreCategory.TRIPLE, (5, 5, 2, 3, 4)),
        (ScoreCategory.QUAD, (4, 4, 4, 2, 3)),
        (ScoreCategory.FULL, (3, 3, 3, 3, 5)),
        (ScoreCategory.EVEN, (2, 2, 4, 4, 5)),
        (ScoreCategory.ODD, (1, 1, 3, 5, 6)),
        (ScoreCategory.SMALL_STRAIGHT, (1, 2, 3, 4, 6)),
        (ScoreCategory.LARGE_STRAIGHT, (1, 2, 3, 4, 5)),
        (ScoreCategory.GAP, (1, 1, 2, 3, 4)),
        (ScoreCategory.POKER, (6, 6, 6, 6, 5)),
    ],
)
def test_invalid_figure_selection_returns_strike_off(
    category: ScoreCategory,
    dice: tuple[int, int, int, int, int],
) -> None:
    result = score(category, make_context(dice))
    assert type(result) is FigureStrikeOffResult


@pytest.mark.unit
def test_player_can_choose_pair_from_hand_with_multiple_available_figures() -> None:
    context = make_context((6, 6, 6, 6, 6))

    pair = score(ScoreCategory.PAIR, context)
    triple = score(ScoreCategory.TRIPLE, context)
    quad = score(ScoreCategory.QUAD, context)
    poker = score(ScoreCategory.POKER, context)

    assert pair == PointsResult(points=12)
    assert triple == PointsResult(points=18)
    assert quad == PointsResult(points=24)
    assert poker == PointsResult(points=100)


@pytest.mark.unit
def test_full_hand_respects_players_explicit_pair_choice() -> None:
    dice = (3, 3, 3, 5, 5)

    pair_of_threes = score(
        ScoreCategory.PAIR,
        make_context(dice),
        pair_value=3,
    )

    pair_of_fives = score(
        ScoreCategory.PAIR,
        make_context(dice),
        pair_value=5,
    )

    two_pairs = score(ScoreCategory.TWO_PAIRS, make_context(dice))
    triple = score(ScoreCategory.TRIPLE, make_context(dice))
    full = score(ScoreCategory.FULL, make_context(dice))

    assert pair_of_threes == PointsResult(points=6)
    assert pair_of_fives == PointsResult(points=10)
    assert two_pairs == PointsResult(points=16)
    assert triple == PointsResult(points=9)
    assert full == PointsResult(points=19)


@pytest.mark.unit
def test_two_pair_hand_respects_players_explicit_pair_choice() -> None:
    dice = (6, 6, 4, 4, 1)

    pair_of_sixes = score(
        ScoreCategory.PAIR,
        make_context(dice),
        pair_value=6,
    )

    pair_of_fours = score(
        ScoreCategory.PAIR,
        make_context(dice),
        pair_value=4,
    )

    assert pair_of_sixes == PointsResult(points=12)
    assert pair_of_fours == PointsResult(points=8)


@pytest.mark.unit
def test_ambiguous_pair_requires_players_explicit_choice() -> None:
    context = make_context((3, 3, 3, 5, 5))

    with pytest.raises(
        AmbiguousFigureSelectionError,
        match="requires pair_value",
    ):
        score(ScoreCategory.PAIR, context)


@pytest.mark.unit
def test_selected_pair_value_must_actually_form_a_pair() -> None:
    context = make_context((6, 6, 2, 3, 4))

    with pytest.raises(
        InvalidFigureSelectionError,
        match="does not form a pair",
    ):
        score(ScoreCategory.PAIR, context, pair_value=4)


@pytest.mark.unit
@pytest.mark.parametrize("pair_value", [0, 7, True])
def test_pair_selection_rejects_illegal_die_value(pair_value: int) -> None:
    context = make_context((6, 6, 2, 3, 4))

    with pytest.raises(InvalidScoreSelectionError, match="integer from 1 to 6"):
        score(ScoreCategory.PAIR, context, pair_value=pair_value)


@pytest.mark.unit
def test_subselection_is_rejected_for_category_that_does_not_need_it() -> None:
    context = make_context((3, 3, 3, 5, 5))

    with pytest.raises(
        InvalidScoreSelectionError,
        match="only valid when scoring Pair",
    ):
        score(ScoreCategory.FULL, context, pair_value=3)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("variant", "face", "points"),
    [
        (PokerScoringVariant.A, 1, 75),
        (PokerScoringVariant.A, 2, 80),
        (PokerScoringVariant.A, 3, 85),
        (PokerScoringVariant.A, 4, 90),
        (PokerScoringVariant.A, 5, 95),
        (PokerScoringVariant.A, 6, 100),
        (PokerScoringVariant.B, 1, 50),
        (PokerScoringVariant.B, 2, 55),
        (PokerScoringVariant.B, 3, 60),
        (PokerScoringVariant.B, 4, 65),
        (PokerScoringVariant.B, 5, 70),
        (PokerScoringVariant.B, 6, 75),
    ],
)
def test_poker_uses_frozen_variant_configuration(
    variant: PokerScoringVariant,
    face: int,
    points: int,
) -> None:
    result = score(
        ScoreCategory.POKER,
        make_context((face, face, face, face, face), poker_variant=variant),
    )

    assert result == PointsResult(points=points)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("category", "dice", "base_points"),
    [
        (ScoreCategory.PAIR, (6, 6, 1, 2, 3), 12),
        (ScoreCategory.CHANCE, (1, 2, 3, 4, 5), 15),
        (ScoreCategory.POKER, (6, 6, 6, 6, 6), 100),
    ],
)
def test_first_roll_doubles_successful_figure_or_chance(
    category: ScoreCategory,
    dice: tuple[int, int, int, int, int],
    base_points: int,
) -> None:
    result = score(category, make_context(dice, roll_number=1))
    assert result == PointsResult(points=base_points * 2)


@pytest.mark.unit
def test_first_roll_does_not_transform_strike_off_into_points() -> None:
    result = score(
        ScoreCategory.POKER,
        make_context((6, 6, 6, 6, 5), roll_number=1),
    )

    assert type(result) is FigureStrikeOffResult


@pytest.mark.unit
def test_registry_is_complete_for_closed_score_category_contract() -> None:
    assert set(REGISTRY) == set(ScoreCategory)


@pytest.mark.unit
def test_unknown_category_is_rejected_without_chance_fallback() -> None:
    context = make_context((6, 6, 6, 6, 6))

    with pytest.raises(UnknownScoreCategory, match="Unknown score category"):
        score("not-a-category", context)  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("balance", "expected"),
    [(-7, -57), (-1, -51), (0, 0), (4, 4)],
)
def test_school_penalty_applies_only_to_negative_final_balance(
    balance: int,
    expected: int,
) -> None:
    assert apply_school_penalty(balance) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("all_completed", "has_strike_off", "expected"),
    [
        (True, False, 100),
        (True, True, 0),
        (False, False, 0),
        (False, True, 0),
    ],
)
def test_figure_completion_bonus_requires_complete_unstruck_set(
    all_completed: bool,
    has_strike_off: bool,
    expected: int,
) -> None:
    assert (
        figure_completion_bonus(
            all_completed=all_completed,
            has_strike_off=has_strike_off,
        )
        == expected
    )
