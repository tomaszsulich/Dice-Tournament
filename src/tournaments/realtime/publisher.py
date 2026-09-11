from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from tournaments.models import Game
from tournaments.realtime.events import TABLE_CHANGED


def table_group_name(game_id: int) -> str:
    return f"table.{game_id}"


def organizer_group_name(tournament_id: int) -> str:
    return f"tournament.{tournament_id}.organizers"


def publish_realtime_event(event_type: str, payload: dict[str, int]) -> None:
    """Deliver a committed state-change hint; PostgreSQL remains authoritative."""
    if event_type != "table_changed":
        return

    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    game = Game.objects.select_related("round").get(pk=payload["game_id"])

    event = {
        "type": TABLE_CHANGED,
        "table_id": game.pk,
        "state_version": payload["state_version"],
    }

    async_to_sync(channel_layer.group_send)(table_group_name(game.pk), event)

    async_to_sync(channel_layer.group_send)(
        organizer_group_name(game.round.tournament_id),
        event,
    )
