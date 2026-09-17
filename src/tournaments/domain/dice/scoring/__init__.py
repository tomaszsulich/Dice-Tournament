from .bonuses import apply_school_penalty, figure_completion_bonus
from .contracts import InvalidScoreSelectionError, ScoreSelection, ScoreStrategy
from .figures import AmbiguousFigureSelectionError, InvalidFigureSelectionError
from .registry import REGISTRY, UnknownScoreCategory, score

__all__ = [
    "AmbiguousFigureSelectionError",
    "InvalidFigureSelectionError",
    "InvalidScoreSelectionError",
    "REGISTRY",
    "ScoreSelection",
    "ScoreStrategy",
    "UnknownScoreCategory",
    "apply_school_penalty",
    "figure_completion_bonus",
    "score",
]
