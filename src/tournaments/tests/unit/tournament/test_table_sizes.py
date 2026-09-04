from itertools import product

import pytest

from tournaments.domain.tournament.table_sizes import (
    MAX_ACTIVE_PARTICIPANTS,
    MAX_TABLE_SIZE,
    MIN_TABLE_SIZE,
    TableSizePlan,
    TableSizePlanningError,
    compute_balanced_table_sizes,
)


@pytest.mark.parametrize(
    ("participants", "expected_sizes"),
    [
        (2, (2,)),
        (3, (3,)),
        (4, (4,)),
        (5, (5,)),
        (6, (6,)),
        (7, (4, 3)),
        (8, (4, 4)),
        (11, (6, 5)),
        (13, (5, 4, 4)),
        (14, (5, 5, 4)),
        (17, (6, 6, 5)),
        (128, (6,) * 18 + (5,) * 4),
    ],
)
def test_compute_balanced_table_sizes_returns_expected_distribution(
    participants,
    expected_sizes,
):
    plan = compute_balanced_table_sizes(
        participants,
        preferred_size=6,
    )

    assert plan == TableSizePlan(
        total=participants,
        sizes=expected_sizes,
        table_count=len(expected_sizes),
    )


@pytest.mark.parametrize("participants", [1, 129])
def test_compute_balanced_table_sizes_rejects_illegal_participant_count(
    participants,
):
    with pytest.raises(TableSizePlanningError):
        compute_balanced_table_sizes(
            participants,
            preferred_size=6,
        )


@pytest.mark.parametrize("preferred_size", [1, 7])
def test_compute_balanced_table_sizes_rejects_illegal_preferred_size(
    preferred_size,
):
    with pytest.raises(TableSizePlanningError):
        compute_balanced_table_sizes(
            8,
            preferred_size=preferred_size,
        )


@pytest.mark.parametrize(
    ("participants", "preferred_size"),
    list(
        product(
            range(MIN_TABLE_SIZE, MAX_ACTIVE_PARTICIPANTS + 1),
            range(MIN_TABLE_SIZE, MAX_TABLE_SIZE + 1),
        ),
    ),
)
def test_every_legal_plan_is_balanced(
    participants,
    preferred_size,
):
    plan = compute_balanced_table_sizes(
        participants,
        preferred_size=preferred_size,
    )

    assert plan.total == participants
    assert sum(plan.sizes) == participants
    assert plan.table_count == len(plan.sizes)

    assert all(MIN_TABLE_SIZE <= size <= MAX_TABLE_SIZE for size in plan.sizes)
    assert max(plan.sizes) - min(plan.sizes) <= 1
    assert plan.sizes == tuple(sorted(plan.sizes, reverse=True))
