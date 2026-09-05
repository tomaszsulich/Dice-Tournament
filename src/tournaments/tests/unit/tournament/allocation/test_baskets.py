import pytest

from tournaments.domain.tournament.allocation.baskets import (
    build_equal_ranking_baskets,
    snake_assignment,
)
from tournaments.domain.tournament.allocation.types import (
    AllocationParticipant,
)


def _participants(count):
    return tuple(
        AllocationParticipant(id=participant_id)
        for participant_id in range(1, count + 1)
    )


def test_build_equal_ranking_baskets_preserves_ranking_layers():
    participants = _participants(10)

    baskets = build_equal_ranking_baskets(
        participants,
        table_count=4,
    )

    assert tuple(
        tuple(participant.id for participant in basket) for basket in baskets
    ) == (
        (1, 2, 3, 4),
        (5, 6, 7, 8),
        (9, 10),
    )


def test_snake_assignment_matches_canonical_sixteen_participant_example():
    participants = _participants(16)

    baskets = build_equal_ranking_baskets(
        participants,
        table_count=4,
    )

    candidate = snake_assignment(
        baskets,
        sizes=(4, 4, 4, 4),
    )

    assert candidate.assignments == (
        (1, 8, 9, 16),
        (2, 7, 10, 15),
        (3, 6, 11, 14),
        (4, 5, 12, 13),
    )


def test_snake_assignment_respects_unequal_balanced_group_sizes():
    participants = _participants(7)

    baskets = build_equal_ranking_baskets(
        participants,
        table_count=2,
    )

    candidate = snake_assignment(
        baskets,
        sizes=(4, 3),
    )

    assert tuple(len(group) for group in candidate.assignments) == (4, 3)

    assert sorted(
        participant_id for group in candidate.assignments for participant_id in group
    ) == list(range(1, 8))


def test_build_equal_ranking_baskets_rejects_non_positive_table_count():
    with pytest.raises(
        ValueError,
        match="Table count must be positive",
    ):
        build_equal_ranking_baskets(
            _participants(4),
            table_count=0,
        )
