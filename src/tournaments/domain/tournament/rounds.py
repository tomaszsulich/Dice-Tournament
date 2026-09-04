from django.db import models


class RoundType(models.TextChoices):
    GROUP = "group", "Group"


class RoundStatus(models.TextChoices):
    WAITING = "waiting", "Waiting"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


ALLOWED_ROUND_STATUS_TRANSITIONS = {
    RoundStatus.WAITING: frozenset(
        {
            RoundStatus.ACTIVE,
            RoundStatus.CANCELLED,
        }
    ),
    RoundStatus.ACTIVE: frozenset(
        {
            RoundStatus.COMPLETED,
            RoundStatus.CANCELLED,
        }
    ),
    RoundStatus.COMPLETED: frozenset(),
    RoundStatus.CANCELLED: frozenset(),
}


def can_transition_round_status(
    current_status: str,
    target_status: str,
) -> bool:
    return target_status in ALLOWED_ROUND_STATUS_TRANSITIONS.get(
        current_status,
        frozenset(),
    )
