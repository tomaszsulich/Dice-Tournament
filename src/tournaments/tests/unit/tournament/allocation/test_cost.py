from tournaments.domain.tournament.allocation.cost import (
    evaluate_candidate,
)
from tournaments.domain.tournament.allocation.types import (
    AllocationCandidate,
    AllocationParticipant,
)


def test_evaluate_candidate_uses_configured_conflict_weights():
    participants = {
        1: AllocationParticipant(
            id=1,
            team_label="Red",
        ),
        2: AllocationParticipant(
            id=2,
            team_label="Red",
        ),
        3: AllocationParticipant(id=3),
        4: AllocationParticipant(id=4),
    }

    baskets = (
        (participants[1], participants[2]),
        (participants[3], participants[4]),
    )

    candidate = AllocationCandidate(
        assignments=((1, 3), (2, 4)),
    )

    evaluation = evaluate_candidate(
        candidate,
        participants,
        baskets,
        sizes=(2, 2),
        repeated_pairs={
            frozenset((1, 3)),
        },
    )

    assert evaluation.cost.repeated_opponents == 1
    assert evaluation.cost.team_conflicts == 0
    assert evaluation.cost.weighted_total == 10


def test_evaluate_candidate_counts_same_team_pairs():
    participants = {
        1: AllocationParticipant(
            id=1,
            team_label="Red",
        ),
        2: AllocationParticipant(id=2),
        3: AllocationParticipant(
            id=3,
            team_label="Red",
        ),
        4: AllocationParticipant(id=4),
    }

    baskets = (
        (participants[1], participants[2]),
        (participants[3], participants[4]),
    )

    candidate = AllocationCandidate(
        assignments=((1, 3), (2, 4)),
    )

    evaluation = evaluate_candidate(
        candidate,
        participants,
        baskets,
        (2, 2),
        set(),
    )

    assert evaluation.cost.team_conflicts == 1
    assert evaluation.cost.weighted_total == 6


def test_hard_constraint_violation_has_infinite_cost():
    participants = {
        participant_id: AllocationParticipant(
            id=participant_id,
        )
        for participant_id in range(1, 5)
    }

    baskets = (
        (participants[1], participants[2]),
        (participants[3], participants[4]),
    )

    candidate = AllocationCandidate(
        assignments=((1, 2), (3, 4)),
    )

    evaluation = evaluate_candidate(
        candidate,
        participants,
        baskets,
        (2, 2),
        set(),
    )

    assert evaluation.cost.weighted_total == float("inf")
    assert evaluation.diagnostics
