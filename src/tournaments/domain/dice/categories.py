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
