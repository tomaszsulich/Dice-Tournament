from collections.abc import Sequence

from tournaments.domain.tournament.allocation.types import (
    AllocationCandidate,
    AllocationParticipant,
)


def build_equal_ranking_baskets(
    participants: Sequence[AllocationParticipant],
    table_count: int,
) -> tuple[tuple[AllocationParticipant, ...], ...]:
    if table_count < 1:
        raise ValueError("Table count must be positive.")

    return tuple(
        tuple(participants[start : start + table_count])
        for start in range(0, len(participants), table_count)
    )


def snake_assignment(
    baskets: Sequence[Sequence[AllocationParticipant]],
    sizes: Sequence[int],
) -> AllocationCandidate:
    groups: list[list[int]] = [[] for _ in sizes]

    for basket_index, basket in enumerate(baskets):
        available_groups = [
            group_index
            for group_index, target_size in enumerate(sizes)
            if len(groups[group_index]) < target_size
        ]

        if basket_index % 2:
            available_groups.reverse()

        if len(basket) > len(available_groups):
            raise ValueError("Basket cannot fit into the remaining group slots.")

        for participant, group_index in zip(
            basket,
            available_groups,
            strict=True,
        ):
            groups[group_index].append(participant.id)

    if any(len(group) != target for group, target in zip(groups, sizes, strict=True)):
        raise ValueError("Snake assignment did not fill the requested group sizes.")

    return AllocationCandidate(
        assignments=tuple(tuple(group) for group in groups),
    )
