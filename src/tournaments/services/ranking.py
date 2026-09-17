from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompletedResult:
    participant_id: int
    score: int


@dataclass(frozen=True, slots=True)
class RankingRow:
    participant_id: int
    total_score: int
    round_scores: tuple[int, ...]
    position: int


def build_ranking(
    completed_results: Iterable[CompletedResult],
) -> tuple[RankingRow, ...]:
    scores_by_participant: dict[int, list[int]] = defaultdict(list)

    for result in completed_results:
        scores_by_participant[result.participant_id].append(result.score)

    ranked = sorted(
        (
            (
                participant_id,
                sum(scores),
                tuple(sorted(scores, reverse=True)),
            )
            for participant_id, scores in scores_by_participant.items()
        ),
        key=lambda row: (-row[1], tuple(-score for score in row[2]), row[0]),
    )

    rows = []
    previous_key: tuple[int, tuple[int, ...]] | None = None
    position = 0

    for index, (participant_id, total_score, round_scores) in enumerate(
        ranked, start=1
    ):
        key = (total_score, round_scores)

        if key != previous_key:
            position = index
            previous_key = key

        rows.append(
            RankingRow(
                participant_id=participant_id,
                total_score=total_score,
                round_scores=round_scores,
                position=position,
            )
        )

    return tuple(rows)
