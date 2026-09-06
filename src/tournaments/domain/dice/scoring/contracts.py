from dataclasses import dataclass
from typing import Protocol

from ..categories import ScoreCategory
from ..context import ScoringContext
from ..result import ScoringResult
from ..types import MAX_DIE_VALUE, MIN_DIE_VALUE


class InvalidScoreSelectionError(ValueError):
    """Raised when an explicit scoring sub-selection is invalid for its category."""


@dataclass(frozen=True, slots=True)
class ScoreSelection:
    category: ScoreCategory
    pair_value: int | None = None

    def __post_init__(self):
        if self.pair_value is None:
            return

        if self.category is not ScoreCategory.PAIR:
            raise InvalidScoreSelectionError(
                "pair_value is only valid when scoring Pair."
            )

        if (
            not isinstance(self.pair_value, int)
            or isinstance(self.pair_value, bool)
            or not MIN_DIE_VALUE <= self.pair_value <= MAX_DIE_VALUE
        ):
            raise InvalidScoreSelectionError(
                f"Pair {self.pair_value!r} must be an integer from "
                f"{MIN_DIE_VALUE} to {MAX_DIE_VALUE}."
            )


class ScoreStrategy(Protocol):
    def score(
        self,
        context: ScoringContext,
        selection: ScoreSelection,
    ) -> ScoringResult: ...
