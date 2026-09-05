import pytest

from tournaments.domain.tournament.allocation.service import (
    generate_group_allocation,
)
from tournaments.domain.tournament.allocation.types import (
    AllocationParticipant,
)


def _participants(count):
    return tuple(
        AllocationParticipant(id=participant_id)
        for participant_id in range(1, count + 1)
    )


@pytest.mark.parametrize(
    "count",
    [16, 64, 128],
)
def test_generate_group_allocation_preserves_balanced_legal_groups(
    count,
):
    result = generate_group_allocation(
        participants=_participants(count),
        preferred_size=6,
        repeated_pairs=set(),
        allocation_seed=20260831,
    )

    sizes = tuple(len(group) for group in result.candidate.assignments)

    assert sum(sizes) == count
    assert min(sizes) >= 2
    assert max(sizes) <= 6
    assert max(sizes) - min(sizes) <= 1


def test_generate_group_allocation_is_reproducible_for_same_seed():
    participants = _participants(16)

    first = generate_group_allocation(
        participants,
        6,
        set(),
        42,
    )

    second = generate_group_allocation(
        participants,
        6,
        set(),
        42,
    )

    assert first == second


def test_generate_group_allocation_rejects_duplicate_participant_ids():
    participants = (
        AllocationParticipant(id=1),
        AllocationParticipant(id=1),
    )

    with pytest.raises(
        ValueError,
        match="Participant ids must be unique",
    ):
        generate_group_allocation(
            participants,
            6,
            set(),
            1,
        )
