from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import (
    ParticipantConnectionStatus,
    ParticipantStatus,
    TournamentStatus,
)
from tournaments.models import Game, Tournament, TournamentParticipant

RECONNECT_GRACE = timedelta(seconds=30)


def decision_deadline_for(
    tournament: Tournament,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """Return the next durable decision deadline for the tournament configuration."""
    seconds = int(tournament.decision_time_limit)

    if seconds <= 0:
        return None

    return (now or timezone.now()) + timedelta(seconds=seconds)


def official_game_for_participant(
    participant: TournamentParticipant,
) -> Game | None:
    """Return the participant's latest server-assigned table."""
    return (
        Game.objects.filter(
            game_participants__tournament_participant=participant,
        )
        .select_related("round__tournament")
        .order_by("-round__number", "-pk")
        .first()
    )


def active_game_for_user(user_id: int) -> Game | None:
    """Return the user's current active official tournament table, if any."""
    participants = TournamentParticipant.objects.filter(
        player_profile__user_id=user_id,
        status=ParticipantStatus.ACTIVE,
        tournament__status=TournamentStatus.ACTIVE,
    ).order_by("pk")

    for participant in participants:
        game = official_game_for_participant(participant)

        if game is not None and game.round.status == RoundStatus.ACTIVE:
            return game

    return None


@transaction.atomic
def mark_connected(
    *,
    participant_id: int,
    channel_name: str,
) -> bool:
    """Mark an active participant connected without reviving ended participation."""
    participant = TournamentParticipant.objects.select_for_update().get(
        pk=participant_id
    )

    if participant.status != ParticipantStatus.ACTIVE:
        return False

    participant.connection_status = ParticipantConnectionStatus.CONNECTED
    participant.disconnected_at = None
    participant.active_connection_channel = channel_name

    participant.save(
        update_fields=(
            "connection_status",
            "disconnected_at",
            "active_connection_channel",
        )
    )

    return True


@transaction.atomic
def mark_reconnecting(
    *,
    participant_id: int,
    channel_name: str,
    now: datetime | None = None,
) -> bool:
    """Start the reconnect grace period for the currently authoritative socket."""
    participant = TournamentParticipant.objects.select_for_update().get(
        pk=participant_id
    )

    if participant.status != ParticipantStatus.ACTIVE:
        return False

    if participant.active_connection_channel != channel_name:
        return False

    participant.connection_status = ParticipantConnectionStatus.RECONNECTING
    participant.disconnected_at = now or timezone.now()
    participant.active_connection_channel = ""

    participant.save(
        update_fields=(
            "connection_status",
            "disconnected_at",
            "active_connection_channel",
        )
    )

    return True


@transaction.atomic
def refresh_connection_status(
    *,
    participant_id: int,
    now: datetime | None = None,
) -> str:
    """Promote an expired reconnect grace period to durable disconnected state."""
    participant = TournamentParticipant.objects.select_for_update().get(
        pk=participant_id
    )

    if participant.status != ParticipantStatus.ACTIVE:
        return participant.connection_status

    current_time = now or timezone.now()

    if (
        participant.connection_status == ParticipantConnectionStatus.RECONNECTING
        and participant.disconnected_at is not None
        and participant.disconnected_at <= current_time - RECONNECT_GRACE
    ):
        participant.connection_status = ParticipantConnectionStatus.DISCONNECTED
        participant.save(update_fields=("connection_status",))

    return participant.connection_status
