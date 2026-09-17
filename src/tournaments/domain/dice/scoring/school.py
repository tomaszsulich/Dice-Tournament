from ..categories import ScoreCategory
from ..context import ScoringContext
from ..result import SchoolSuccessResult
from .contracts import ScoreSelection


class OnesStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> SchoolSuccessResult:
        return _score_school(context, ScoreCategory.ONES, 1)


class TwosStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> SchoolSuccessResult:
        return _score_school(context, ScoreCategory.TWOS, 2)


class ThreesStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> SchoolSuccessResult:
        return _score_school(context, ScoreCategory.THREES, 3)


class FoursStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> SchoolSuccessResult:
        return _score_school(context, ScoreCategory.FOURS, 4)


class FivesStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> SchoolSuccessResult:
        return _score_school(context, ScoreCategory.FIVES, 5)


class SixesStrategy:
    def score(
        self,
        context: ScoringContext,
        _selection: ScoreSelection,
    ) -> SchoolSuccessResult:
        return _score_school(context, ScoreCategory.SIXES, 6)


def _score_school(
    context: ScoringContext,
    category: ScoreCategory,
    face: int,
):
    matching_dice = context.dice.counts.get(face, 0)
    balance = (matching_dice - 3) * face
    return SchoolSuccessResult(category=category, balance=balance)
