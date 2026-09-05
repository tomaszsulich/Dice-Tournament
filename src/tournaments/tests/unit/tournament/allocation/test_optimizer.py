from itertools import combinations
from random import Random

from tournaments.domain.tournament.allocation.baskets import (
    build_equal_ranking_baskets,
    snake_assignment,
)
from tournaments.domain.tournament.allocation.cost import (
    evaluate_candidate,
)
from tournaments.domain.tournament.allocation.optimizer import (
    _adjacent_basket_candidates,
    optimize_allocation,
)
from tournaments.domain.tournament.allocation.types import (
    AllocationParticipant,
)


def _setup(count=8):
    participants = tuple(
        AllocationParticipant(id=participant_id)
        for participant_id in range(1, count + 1)
    )

    participant_map = {participant.id: participant for participant in participants}

    baskets = build_equal_ranking_baskets(
        participants,
        table_count=2,
    )

    initial = snake_assignment(
        baskets,
        sizes=(count // 2, count // 2),
    )

    return participant_map, baskets, initial


def test_optimizer_selects_unique_better_variant():
    participants, baskets, initial = _setup(4)

    repeated_pairs = {
        frozenset((1, 4)),
    }

    result = optimize_allocation(
        initial,
        participants,
        baskets,
        sizes=(2, 2),
        repeated_pairs=repeated_pairs,
        rng=Random(1),
    )

    result_pairs = {
        frozenset(pair)
        for group in result.candidate.assignments
        for pair in combinations(group, 2)
    }

    assert result.cost.weighted_total == 0
    assert frozenset((1, 4)) not in result_pairs


def test_equal_best_variants_are_reproducible_for_same_seed():
    participants, baskets, initial = _setup(4)

    first = optimize_allocation(
        initial,
        participants,
        baskets,
        (2, 2),
        set(),
        Random(7),
    )

    second = optimize_allocation(
        initial,
        participants,
        baskets,
        (2, 2),
        set(),
        Random(7),
    )

    assert first == second


def test_equal_best_variants_can_differ_for_different_seeds():
    participants, baskets, initial = _setup(4)

    results = {
        optimize_allocation(
            initial,
            participants,
            baskets,
            (2, 2),
            set(),
            Random(seed),
        ).candidate
        for seed in range(10)
    }

    assert len(results) >= 2


def test_optimizer_never_returns_worse_cost_than_initial_candidate():
    participants, baskets, initial = _setup(8)

    repeated_pairs = {
        frozenset((1, 4)),
        frozenset((2, 3)),
        frozenset((5, 8)),
    }

    initial_evaluation = evaluate_candidate(
        initial,
        participants,
        baskets,
        (4, 4),
        repeated_pairs,
    )

    result = optimize_allocation(
        initial,
        participants,
        baskets,
        (4, 4),
        repeated_pairs,
        Random(3),
    )

    assert result.cost.weighted_total <= initial_evaluation.cost.weighted_total


def test_adjacent_search_never_crosses_more_than_one_basket_boundary():
    _participants, baskets, initial = _setup(8)

    basket_by_participant = {
        participant.id: basket_index
        for basket_index, basket in enumerate(baskets)
        for participant in basket
    }

    for candidate in _adjacent_basket_candidates(
        initial,
        baskets,
    ):
        moved = {
            participant_id
            for group_index, group in enumerate(candidate.assignments)
            for participant_id in group
            if participant_id not in initial.assignments[group_index]
        }

        moved_baskets = {
            basket_by_participant[participant_id] for participant_id in moved
        }

        assert len(moved_baskets) == 2
        assert max(moved_baskets) - min(moved_baskets) == 1
