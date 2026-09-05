from dataclasses import dataclass

type ParticipantId = int
type Assignment = tuple[tuple[ParticipantId, ...], ...]
type RepeatedPair = frozenset[ParticipantId]


@dataclass(frozen=True)
class AllocationParticipant:
    id: ParticipantId
    team_label: str = ""


@dataclass(frozen=True)
class AllocationCandidate:
    assignments: Assignment


@dataclass(frozen=True)
class AllocationCost:
    repeated_opponents: int
    team_conflicts: int
    weighted_total: int | float


@dataclass(frozen=True)
class AllocationEvaluation:
    candidate: AllocationCandidate
    cost: AllocationCost
    diagnostics: tuple[str, ...] = ()
