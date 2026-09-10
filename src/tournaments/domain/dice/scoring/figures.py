from collections.abc import Mapping

from ..categories import PokerScoringVariant
from ..context import ScoringContext
from ..result import FigureStrikeOffResult, PointsResult, ScoringResult
from .contracts import ScoreSelection


class AmbiguousFigureSelectionError(ValueError):
    """Raised when scoring needs an explicit player choice to stay deterministic."""


class InvalidFigureSelectionError(ValueError):
    """Raised when the player selects a value unavailable for the chosen figure."""


class PairStrategy:
    def score(
        self,
        context: ScoringContext,
        selection: ScoreSelection,
    ) -> ScoringResult:
        eligible = _values_with_minimum_count(context.dice.counts, 2)

        if not eligible:
            return FigureStrikeOffResult()

        if selection.pair_value is not None:
            if selection.pair_value not in eligible:
                raise InvalidFigureSelectionError(
                    "Selected Pair value does not form a pair in the current dice."
                )

            pair_value = selection.pair_value

        elif len(eligible) == 1:
            pair_value = eligible[0]

        else:
            raise AmbiguousFigureSelectionError(
                "Pair scoring requires pair_value when more than one pair is available."
            )

        return PointsResult(points=2 * pair_value)


class TwoPairsStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        pairs = [
            value
            for value, count in context.dice.counts.items()
            for _ in range(count // 2)
        ]

        if len(pairs) < 2:
            return FigureStrikeOffResult()

        return PointsResult(points=2 * sum(sorted(pairs, reverse=True)[:2]))


class TripleStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        value = _single_value_with_minimum_count(context.dice.counts, 3)

        if value is None:
            return FigureStrikeOffResult()

        return PointsResult(points=3 * value)


class QuadStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        value = _single_value_with_minimum_count(context.dice.counts, 4)

        if value is None:
            return FigureStrikeOffResult()

        return PointsResult(points=4 * value)


class FullStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        if sorted(context.dice.counts.values()) != [2, 3]:
            return FigureStrikeOffResult()
        return PointsResult(points=context.dice.total)


class EvenStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        if any(value % 2 for value in context.dice.dice):
            return FigureStrikeOffResult()
        return PointsResult(points=context.dice.total)


class OddStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        if any(value % 2 == 0 for value in context.dice.dice):
            return FigureStrikeOffResult()
        return PointsResult(points=context.dice.total)


class SmallStraightStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        if context.dice.sorted_values != (1, 2, 3, 4, 5):
            return FigureStrikeOffResult()
        return PointsResult(points=15)


class LargeStraightStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        if context.dice.sorted_values != (2, 3, 4, 5, 6):
            return FigureStrikeOffResult()
        return PointsResult(points=20)


class GapStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        if len(context.dice.unique) != 5:
            return FigureStrikeOffResult()
        return PointsResult(points=context.dice.total)


class ChanceStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ):
        return PointsResult(points=context.dice.total)


class PokerStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> ScoringResult:
        if len(context.dice.unique) != 1:
            return FigureStrikeOffResult()

        value = context.dice.dice[0]
        points = _POKER_POINTS[context.config.poker_variant][value]
        return PointsResult(points=points)


_POKER_POINTS: dict[PokerScoringVariant, dict[int, int]] = {
    PokerScoringVariant.A: {1: 75, 2: 80, 3: 85, 4: 90, 5: 95, 6: 100},
    PokerScoringVariant.B: {1: 50, 2: 55, 3: 60, 4: 65, 5: 70, 6: 75},
}


def _values_with_minimum_count(counts: Mapping[int, int], minimum: int) -> list[int]:
    return [value for value, count in counts.items() if count >= minimum]


def _single_value_with_minimum_count(
    counts: Mapping[int, int], minimum: int
) -> int | None:
    eligible = _values_with_minimum_count(counts, minimum)
    return eligible[0] if eligible else None
