from django.db.models import F

from tournaments.models import Game

TABLE_CHANGED = "table.changed"


def bump_game_state_version(game_id: int) -> int:
    """Advance and return the durable table version inside the caller transaction."""
    Game.objects.filter(pk=game_id).update(state_version=F("state_version") + 1)
    return Game.objects.values_list("state_version", flat=True).get(pk=game_id)
