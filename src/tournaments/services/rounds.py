from django.core.exceptions import ValidationError
from django.utils import timezone

from tournaments.domain.tournament.rounds import (
    RoundStatus,
    can_transition_round_status,
)
from tournaments.models import Round


def _transition_round(
    round_: Round,
    target_status: str,
) -> Round:
    if not can_transition_round_status(round_.status, target_status):
        raise ValidationError(
            f"Round cannot transition from {round_.status} to {target_status}."
        )

    round_.status = target_status
    update_fields = ["status"]

    if target_status == RoundStatus.ACTIVE:
        round_.started_at = timezone.now()
        update_fields.append("started_at")

    if target_status in {
        RoundStatus.COMPLETED,
        RoundStatus.CANCELLED,
    }:
        round_.ended_at = timezone.now()
        update_fields.append("ended_at")

    round_.save(update_fields=update_fields)
    return round_


def start_round(round_: Round) -> Round:
    return _transition_round(round_, RoundStatus.ACTIVE)


def complete_round(round_: Round) -> Round:
    return _transition_round(round_, RoundStatus.COMPLETED)


def cancel_round(round_: Round) -> Round:
    return _transition_round(round_, RoundStatus.CANCELLED)
