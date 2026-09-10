from enum import StrEnum


class ScoreCategory(StrEnum):
    ONES = "ones"
    TWOS = "twos"
    THREES = "threes"
    FOURS = "fours"
    FIVES = "fives"
    SIXES = "sixes"
    PAIR = "pair"
    TWO_PAIRS = "two_pairs"
    TRIPLE = "triple"
    QUAD = "quad"
    FULL = "full"
    EVEN = "even"
    ODD = "odd"
    SMALL_STRAIGHT = "small_straight"
    LARGE_STRAIGHT = "large_straight"
    GAP = "gap"
    CHANCE = "chance"
    POKER = "poker"

    @property
    def label(self) -> str:
        return _CATEGORY_LABELS[self]

    @property
    def information(self) -> str | None:
        return _CATEGORY_INFORMATION.get(self)


_CATEGORY_LABELS: dict[ScoreCategory, str] = {
    ScoreCategory.ONES: "1",
    ScoreCategory.TWOS: "2",
    ScoreCategory.THREES: "3",
    ScoreCategory.FOURS: "4",
    ScoreCategory.FIVES: "5",
    ScoreCategory.SIXES: "6",
    ScoreCategory.PAIR: "Pair",
    ScoreCategory.TWO_PAIRS: "Two Pairs",
    ScoreCategory.TRIPLE: "Triple",
    ScoreCategory.QUAD: "Quad",
    ScoreCategory.FULL: "Full",
    ScoreCategory.EVEN: "Even",
    ScoreCategory.ODD: "Odd",
    ScoreCategory.SMALL_STRAIGHT: "Small Straight",
    ScoreCategory.LARGE_STRAIGHT: "Large Straight",
    ScoreCategory.GAP: "Gap",
    ScoreCategory.CHANCE: "Chance",
    ScoreCategory.POKER: "Poker",
}


_CATEGORY_INFORMATION: dict[ScoreCategory, str] = {
    ScoreCategory.ONES: (
        "Target (X): three ones.\n"
        "Each missing/extra one: −1/+1.\n"
        "Range: −3\u00a0to\u00a0+2."
    ),
    ScoreCategory.TWOS: (
        "Target (X): three twos.\n"
        "Each missing/extra two: −2/+2.\n"
        "Range: −6\u00a0to\u00a0+4."
    ),
    ScoreCategory.THREES: (
        "Target (X): three threes.\n"
        "Each missing/extra three: −3/+3.\n"
        "Range: −9\u00a0to\u00a0+6."
    ),
    ScoreCategory.FOURS: (
        "Target (X): three fours.\n"
        "Each missing/extra four: −4/+4.\n"
        "Range: −12\u00a0to\u00a0+8."
    ),
    ScoreCategory.FIVES: (
        "Target (X): three fives.\n"
        "Each missing/extra five: −5/+5.\n"
        "Range: −15\u00a0to\u00a0+10."
    ),
    ScoreCategory.SIXES: (
        "Target (X): three sixes.\n"
        "Each missing/extra six: −6/+6.\n"
        "Range: −18\u00a0to\u00a0+12."
    ),
    ScoreCategory.PAIR: (
        "Two matching dice: 2× chosen value.\nMultiple pairs: choose one.\nNo pair: X."
    ),
    ScoreCategory.TWO_PAIRS: (
        "Two distinct pairs: sum of their four dice.\nOtherwise: X."
    ),
    ScoreCategory.TRIPLE: "At least three matching dice: 3× value.\nOtherwise: X.",
    ScoreCategory.QUAD: "At least four matching dice: 4× value.\nOtherwise: X.",
    ScoreCategory.FULL: (
        "Three matching dice + a\u00a0separate pair: sum of all 5\u00a0dice.\n"
        "Otherwise: X."
    ),
    ScoreCategory.EVEN: (
        "All 5\u00a0dice even: sum of all 5\u00a0dice.\nOtherwise: X."
    ),
    ScoreCategory.ODD: ("All 5\u00a0dice odd: sum of all 5\u00a0dice.\nOtherwise: X."),
    ScoreCategory.SMALL_STRAIGHT: (
        "Exactly 1, 2, 3, 4, 5: 15\u00a0points.\nOtherwise: X."
    ),
    ScoreCategory.LARGE_STRAIGHT: (
        "Exactly 2, 3, 4, 5, 6: 20\u00a0points.\nOtherwise: X."
    ),
    ScoreCategory.GAP: (
        "All 5\u00a0dice different: sum of all 5\u00a0dice.\nOtherwise: X."
    ),
    ScoreCategory.CHANCE: "Any combination: sum of all 5\u00a0dice.",
    ScoreCategory.POKER: (
        "All 5\u00a0dice match.\nPoints follow the tournament variant.\nOtherwise: X."
    ),
}


SCHOOL_SECTION_INFORMATION = (
    "Negative final balance: −50\u00a0points.\nNo 1st\u00a0roll multiplier."
)

FIGURES_SECTION_INFORMATION = (
    "1st\u00a0roll: ×2. All figures without X: +100\u00a0points."
)


SCHOOL_CATEGORIES: frozenset[ScoreCategory] = frozenset(
    {
        ScoreCategory.ONES,
        ScoreCategory.TWOS,
        ScoreCategory.THREES,
        ScoreCategory.FOURS,
        ScoreCategory.FIVES,
        ScoreCategory.SIXES,
    }
)


class PokerScoringVariant(StrEnum):
    A = "a"
    B = "b"
