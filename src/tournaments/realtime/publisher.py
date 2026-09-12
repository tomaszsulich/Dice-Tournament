from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.urls import reverse

from tournaments.models import Game, Round
from tournaments.realtime.events import TABLE_ASSIGNMENT_CHANGED, TABLE_CHANGED


def table_group_name(game_id: int) -> str:
    return f"table.{game_id}"


def organizer_group_name(tournament_id: int) -> str:
    return f"tournament.{tournament_id}.organizers"


def participant_group_name(participant_id: int) -> str:
    return f"participant.{participant_id}.assignment"


def publish_realtime_event(event_type: str, payload: dict[str, object]) -> None:
    """Deliver committed state-change hints; PostgreSQL remains authoritative."""
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    if event_type == "table_changed":
        _publish_table_changed(channel_layer, payload)
        return

    if event_type == "round_transition":
        _publish_round_assignments(channel_layer, payload)


def _publish_table_changed(channel_layer, payload: dict[str, object]) -> None:
    game_id = int(payload["game_id"])
    state_version = int(payload["state_version"])
    game = Game.objects.select_related("round").get(pk=game_id)

    event = {
        "type": TABLE_CHANGED,
        "table_id": game.pk,
        "state_version": state_version,
    }

    async_to_sync(channel_layer.group_send)(table_group_name(game.pk), event)

    async_to_sync(channel_layer.group_send)(
        organizer_group_name(game.round.tournament_id),
        event,
    )


def _publish_round_assignments(channel_layer, payload: dict[str, object]) -> None:
    round_id = int(payload["round_id"])
    round_ = Round.objects.select_related("tournament").get(pk=round_id)

    assignments = (
        Game.objects.filter(round=round_)
        .prefetch_related("game_participants")
        .order_by("pk")
    )

    for game in assignments:
        event = {
            "type": TABLE_ASSIGNMENT_CHANGED,
            "table_id": game.pk,
            "state_version": game.state_version,
            "target_url": reverse("participant-table", args=(game.pk,)),
        }

        for game_participant in game.game_participants.all():
            async_to_sync(channel_layer.group_send)(
                participant_group_name(game_participant.tournament_participant_id),
                event,
            )
