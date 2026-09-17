from dataclasses import dataclass

from .categories import SCHOOL_CATEGORIES, ScoreCategory


@dataclass(frozen=True, slots=True)
class PointsResult:
    points: int


@dataclass(frozen=True, slots=True)
class SchoolSuccessResult:
    category: ScoreCategory
    balance: int

    def __post_init__(self):
        if self.category not in SCHOOL_CATEGORIES:
            raise ValueError("School result requires one of the 1-6 school categories.")


@dataclass(frozen=True, slots=True)
class FigureStrikeOffResult:
    pass


type ScoringResult = PointsResult | SchoolSuccessResult | FigureStrikeOffResult
