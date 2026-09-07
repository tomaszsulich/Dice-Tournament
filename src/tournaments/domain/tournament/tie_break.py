from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from tournaments.services.ranking import RankingRow


class ChoiceSource(Protocol):
    def choice(self, values: Sequence[int]) -> int: ...


@dataclass(frozen=True, slots=True)
class MaterialTie:
    participant_ids: tuple[int, ...]


def top_material_tie(ranking: Sequence[RankingRow]):
    if not ranking:
        return None

    first_position = ranking[0].position

    tied = tuple(
        row.participant_id for row in ranking if row.position == first_position
    )

    if len(tied) < 2:
        return None

    return MaterialTie(participant_ids=tied)


def controlled_draw(participant_ids: Sequence[int], rng: ChoiceSource) -> int:
    candidates = tuple(sorted(set(participant_ids)))

    if len(candidates) < 2:
        raise ValueError("A controlled draw requires at least two tied participants.")

    return rng.choice(candidates)
