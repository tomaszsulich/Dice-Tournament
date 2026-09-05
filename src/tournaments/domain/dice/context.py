from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .categories import PokerScoringVariant
from .types import Dice, make_dice

MIN_ROLL_NUMBER = 1
MAX_ROLL_NUMBER = 3


class InvalidRollNumberError(ValueError):
    """Raised when a scoring context uses a roll outside the legal turn range."""


@dataclass(frozen=True, slots=True)
class DiceContext:
    dice: Dice
    counts: Mapping[int, int]
    total: int
    unique: frozenset[int]
    sorted_values: Dice

    @classmethod
    def from_values(cls, values: Iterable[int]) -> "DiceContext":
        dice = make_dice(values)
        counts, total, unique, sorted_values = _analyze_dice(dice)
        return cls(
            dice=dice,
            counts=counts,
            total=total,
            unique=unique,
            sorted_values=sorted_values,
        )


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    poker_variant: PokerScoringVariant


@dataclass(frozen=True, slots=True)
class ScoringContext:
    dice: DiceContext
    roll_number: int
    config: ScoringConfig

    def __post_init__(self) -> None:
        if not MIN_ROLL_NUMBER <= self.roll_number <= MAX_ROLL_NUMBER:
            raise InvalidRollNumberError(
                f"Roll number must be between {MIN_ROLL_NUMBER} and {MAX_ROLL_NUMBER}."
            )


def _analyze_dice(dice: Dice) -> tuple[Mapping[int, int], int, frozenset[int], Dice]:
    counts = MappingProxyType(dict(Counter(dice)))

    total = sum(dice)
    unique = frozenset(dice)
    sorted_values = tuple(sorted(dice))

    return counts, total, unique, sorted_values
