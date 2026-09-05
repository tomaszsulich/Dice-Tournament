from collections.abc import Collection, Sequence
from random import Random

from tournaments.domain.tournament.allocation.baskets import (
    build_equal_ranking_baskets,
    snake_assignment,
)
from tournaments.domain.tournament.allocation.optimizer import (
    optimize_allocation,
)
from tournaments.domain.tournament.allocation.types import (
    AllocationEvaluation,
    AllocationParticipant,
    RepeatedPair,
)
from tournaments.domain.tournament.table_sizes import (
    compute_balanced_table_sizes,
)


def generate_group_allocation(
    participants: Sequence[AllocationParticipant],
    preferred_size: int,
    repeated_pairs: Collection[RepeatedPair],
    allocation_seed: int,
) -> AllocationEvaluation:
    size_plan = compute_balanced_table_sizes(
        len(participants),
        preferred_size,
    )

    baskets = build_equal_ranking_baskets(
        participants,
        size_plan.table_count,
    )

    initial = snake_assignment(
        baskets,
        size_plan.sizes,
    )

    participant_map = {participant.id: participant for participant in participants}

    if len(participant_map) != len(participants):
        raise ValueError("Participant ids must be unique.")

    return optimize_allocation(
        initial=initial,
        participants=participant_map,
        baskets=baskets,
        sizes=size_plan.sizes,
        repeated_pairs=repeated_pairs,
        rng=Random(allocation_seed),
    )
