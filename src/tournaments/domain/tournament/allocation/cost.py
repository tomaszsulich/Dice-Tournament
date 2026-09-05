from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from itertools import combinations

from tournaments.domain.tournament.allocation.types import (
    AllocationCandidate,
    AllocationCost,
    AllocationEvaluation,
    AllocationParticipant,
    RepeatedPair,
)

REPEATED_OPPONENT_WEIGHT = 10
TEAM_CONFLICT_WEIGHT = 6


def _hard_constraint_diagnostics(
    candidate: AllocationCandidate,
    baskets: Sequence[Sequence[AllocationParticipant]],
    sizes: Sequence[int],
) -> tuple[str, ...]:
    diagnostics = []

    if len(candidate.assignments) != len(sizes):
        diagnostics.append("Candidate has an invalid number of groups.")
        return tuple(diagnostics)

    actual_sizes = tuple(len(group) for group in candidate.assignments)

    if actual_sizes != tuple(sizes):
        diagnostics.append("Candidate does not preserve requested group sizes.")

    expected_ids = [participant.id for basket in baskets for participant in basket]
    actual_ids = [
        participant_id for group in candidate.assignments for participant_id in group
    ]

    if Counter(actual_ids) != Counter(expected_ids):
        diagnostics.append("Every participant must occur in exactly one group.")

    group_by_participant = {
        participant_id: group_index
        for group_index, group in enumerate(candidate.assignments)
        for participant_id in group
    }

    for basket in baskets:
        basket_groups = [
            group_by_participant.get(participant.id) for participant in basket
        ]

        if None not in basket_groups and len(set(basket_groups)) != len(basket_groups):
            diagnostics.append(
                "A group contains more than one participant from a basket."
            )
            break

    return tuple(diagnostics)


def evaluate_candidate(
    candidate: AllocationCandidate,
    participants: Mapping[int, AllocationParticipant],
    baskets: Sequence[Sequence[AllocationParticipant]],
    sizes: Sequence[int],
    repeated_pairs: Collection[RepeatedPair],
) -> AllocationEvaluation:
    diagnostics = _hard_constraint_diagnostics(
        candidate,
        baskets,
        sizes,
    )

    if diagnostics:
        return AllocationEvaluation(
            candidate=candidate,
            cost=AllocationCost(
                repeated_opponents=0,
                team_conflicts=0,
                weighted_total=float("inf"),
            ),
            diagnostics=diagnostics,
        )

    repeated_opponents = 0
    team_conflicts = 0
    repeated_pair_set = set(repeated_pairs)

    for group in candidate.assignments:
        for first_id, second_id in combinations(group, 2):
            if frozenset((first_id, second_id)) in repeated_pair_set:
                repeated_opponents += 1

            first_team = participants[first_id].team_label
            second_team = participants[second_id].team_label

            if first_team and first_team == second_team:
                team_conflicts += 1

    weighted_total = (
        repeated_opponents * REPEATED_OPPONENT_WEIGHT
        + team_conflicts * TEAM_CONFLICT_WEIGHT
    )

    soft_diagnostics = []

    if repeated_opponents:
        soft_diagnostics.append(f"Repeated opponent pairs: {repeated_opponents}.")

    if team_conflicts:
        soft_diagnostics.append(f"Same-team pairs: {team_conflicts}.")

    return AllocationEvaluation(
        candidate=candidate,
        cost=AllocationCost(
            repeated_opponents=repeated_opponents,
            team_conflicts=team_conflicts,
            weighted_total=weighted_total,
        ),
        diagnostics=tuple(soft_diagnostics),
    )
