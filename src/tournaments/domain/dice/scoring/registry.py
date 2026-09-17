from ..categories import SCHOOL_CATEGORIES, ScoreCategory
from ..context import ScoringContext
from ..result import PointsResult, ScoringResult
from .contracts import ScoreSelection, ScoreStrategy
from .figures import (
    ChanceStrategy,
    EvenStrategy,
    FullStrategy,
    GapStrategy,
    LargeStraightStrategy,
    OddStrategy,
    PairStrategy,
    PokerStrategy,
    QuadStrategy,
    SmallStraightStrategy,
    TripleStrategy,
    TwoPairsStrategy,
)
from .school import (
    FivesStrategy,
    FoursStrategy,
    OnesStrategy,
    SixesStrategy,
    ThreesStrategy,
    TwosStrategy,
)


class UnknownScoreCategory(ValueError):
    """Raised when scoring is requested for a category outside the closed registry."""


REGISTRY: dict[ScoreCategory, ScoreStrategy] = {
    ScoreCategory.ONES: OnesStrategy(),
    ScoreCategory.TWOS: TwosStrategy(),
    ScoreCategory.THREES: ThreesStrategy(),
    ScoreCategory.FOURS: FoursStrategy(),
    ScoreCategory.FIVES: FivesStrategy(),
    ScoreCategory.SIXES: SixesStrategy(),
    ScoreCategory.PAIR: PairStrategy(),
    ScoreCategory.TWO_PAIRS: TwoPairsStrategy(),
    ScoreCategory.TRIPLE: TripleStrategy(),
    ScoreCategory.QUAD: QuadStrategy(),
    ScoreCategory.FULL: FullStrategy(),
    ScoreCategory.EVEN: EvenStrategy(),
    ScoreCategory.ODD: OddStrategy(),
    ScoreCategory.SMALL_STRAIGHT: SmallStraightStrategy(),
    ScoreCategory.LARGE_STRAIGHT: LargeStraightStrategy(),
    ScoreCategory.GAP: GapStrategy(),
    ScoreCategory.CHANCE: ChanceStrategy(),
    ScoreCategory.POKER: PokerStrategy(),
}


def score(
    category: ScoreCategory,
    context: ScoringContext,
    *,
    pair_value: int | None = None,
) -> ScoringResult:
    strategy = REGISTRY.get(category)

    if strategy is None:
        raise UnknownScoreCategory(f"Unknown score category: {category!r}")

    selection = ScoreSelection(category=category, pair_value=pair_value)
    result = strategy.score(context, selection)

    if category in SCHOOL_CATEGORIES:
        return result

    if context.roll_number == 1 and isinstance(result, PointsResult):
        return PointsResult(points=result.points * 2)

    return result
