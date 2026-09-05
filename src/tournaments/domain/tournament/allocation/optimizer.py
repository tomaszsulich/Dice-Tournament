from collections.abc import Collection, Mapping, Sequence
from itertools import permutations
from random import Random

from tournaments.domain.tournament.allocation.cost import evaluate_candidate
from tournaments.domain.tournament.allocation.types import (
    AllocationCandidate,
    AllocationEvaluation,
    AllocationParticipant,
    RepeatedPair,
)

MAX_LOCAL_PASSES = 100
MAX_CANDIDATES_PER_PASS = 5000


def optimize_allocation(
    initial: AllocationCandidate,
    participants: Mapping[int, AllocationParticipant],
    baskets: Sequence[Sequence[AllocationParticipant]],
    sizes: Sequence[int],
    repeated_pairs: Collection[RepeatedPair],
    rng: Random,
) -> AllocationEvaluation:
    current = evaluate_candidate(
        initial,
        participants,
        baskets,
        sizes,
        repeated_pairs,
    )

    for _ in range(MAX_LOCAL_PASSES):
        local_best = _best_evaluation(
            (
                current.candidate,
                *_within_basket_candidates(
                    current.candidate,
                    baskets,
                ),
            ),
            participants,
            baskets,
            sizes,
            repeated_pairs,
            rng,
        )

        if local_best.cost.weighted_total < current.cost.weighted_total:
            current = local_best
            continue

        current = local_best

        if current.cost.weighted_total == 0:
            break

        adjacent_best = _best_evaluation(
            (
                current.candidate,
                *_adjacent_basket_candidates(
                    current.candidate,
                    baskets,
                ),
            ),
            participants,
            baskets,
            sizes,
            repeated_pairs,
            rng,
        )

        if adjacent_best.cost.weighted_total < current.cost.weighted_total:
            current = adjacent_best
            continue

        break

    return current


def _best_evaluation(
    candidates: Sequence[AllocationCandidate],
    participants: Mapping[int, AllocationParticipant],
    baskets: Sequence[Sequence[AllocationParticipant]],
    sizes: Sequence[int],
    repeated_pairs: Collection[RepeatedPair],
    rng: Random,
) -> AllocationEvaluation:
    unique_candidates = sorted(
        set(candidates),
        key=lambda candidate: candidate.assignments,
    )[:MAX_CANDIDATES_PER_PASS]

    evaluations = [
        evaluate_candidate(
            candidate,
            participants,
            baskets,
            sizes,
            repeated_pairs,
        )
        for candidate in unique_candidates
    ]

    best_total = min(evaluation.cost.weighted_total for evaluation in evaluations)

    best = [
        evaluation
        for evaluation in evaluations
        if evaluation.cost.weighted_total == best_total
    ]

    if len(best) == 1:
        return best[0]

    return rng.choice(best)


def _within_basket_candidates(
    candidate: AllocationCandidate,
    baskets: Sequence[Sequence[AllocationParticipant]],
) -> tuple[AllocationCandidate, ...]:
    group_by_participant = _group_index(candidate)
    candidates = []

    for basket in baskets:
        participant_ids = tuple(participant.id for participant in basket)

        group_indexes = tuple(
            group_by_participant[participant_id] for participant_id in participant_ids
        )

        for permuted_ids in permutations(participant_ids):
            if permuted_ids == participant_ids:
                continue

            replacements = dict(
                zip(
                    group_indexes,
                    permuted_ids,
                    strict=True,
                )
            )

            candidates.append(
                _replace_basket_members(
                    candidate,
                    participant_ids,
                    replacements,
                )
            )

            if len(candidates) >= MAX_CANDIDATES_PER_PASS:
                return tuple(candidates)

    return tuple(candidates)


def _adjacent_basket_candidates(
    candidate: AllocationCandidate,
    baskets: Sequence[Sequence[AllocationParticipant]],
) -> tuple[AllocationCandidate, ...]:
    group_by_participant = _group_index(candidate)
    candidates = []

    for left_basket, right_basket in zip(
        baskets,
        baskets[1:],
    ):
        for left in left_basket:
            for right in right_basket:
                if group_by_participant[left.id] == group_by_participant[right.id]:
                    continue

                candidates.append(
                    _swap_participants(
                        candidate,
                        left.id,
                        right.id,
                    )
                )

                if len(candidates) >= MAX_CANDIDATES_PER_PASS:
                    return tuple(candidates)

    return tuple(candidates)


def _group_index(
    candidate: AllocationCandidate,
) -> dict[int, int]:
    return {
        participant_id: group_index
        for group_index, group in enumerate(candidate.assignments)
        for participant_id in group
    }


def _replace_basket_members(
    candidate: AllocationCandidate,
    participant_ids: tuple[int, ...],
    replacements: Mapping[int, int],
) -> AllocationCandidate:
    participant_id_set = set(participant_ids)
    groups = [list(group) for group in candidate.assignments]

    for group_index, group in enumerate(groups):
        for position, participant_id in enumerate(group):
            if participant_id in participant_id_set:
                group[position] = replacements[group_index]

    return AllocationCandidate(
        assignments=tuple(tuple(group) for group in groups),
    )


def _swap_participants(
    candidate: AllocationCandidate,
    first_id: int,
    second_id: int,
) -> AllocationCandidate:
    groups = [list(group) for group in candidate.assignments]

    for group in groups:
        for position, participant_id in enumerate(group):
            if participant_id == first_id:
                group[position] = second_id
            elif participant_id == second_id:
                group[position] = first_id

    return AllocationCandidate(
        assignments=tuple(tuple(group) for group in groups),
    )
