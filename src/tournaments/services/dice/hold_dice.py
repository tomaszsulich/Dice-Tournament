from collections.abc import Callable

from django.db import transaction

from accounts.models import User
from tournaments.domain.tournament.types import TournamentStatus
from tournaments.models import Game, Turn

type HeldDice = tuple[bool, bool, bool, bool, bool]
type Publisher = Callable[[str, dict[str, int]], None]


class HoldCommandError(Exception):
    code = "HOLD_COMMAND_ERROR"


class GameNotFound(HoldCommandError):
    code = "GAME_NOT_FOUND"


class HoldForbidden(HoldCommandError):
    code = "NOT_YOUR_TURN"


class HoldUnavailable(HoldCommandError):
    code = "HOLD_UNAVAILABLE"


class InvalidHoldPayload(HoldCommandError):
    code = "INVALID_HOLD_PAYLOAD"


def set_held_dice(
    *,
    user: User,
    game_id: int,
    held_flags: HeldDice,
    publisher: Publisher,
) -> dict[str, object]:
    if not getattr(user, "is_authenticated", False):
        raise HoldForbidden

    if len(held_flags) != 5 or any(type(value) is not bool for value in held_flags):
        raise InvalidHoldPayload

    with transaction.atomic():
        turn = _lock_current_turn(game_id)
        _require_legal_hold(turn, user)

        for position, held in enumerate(held_flags, start=1):
            setattr(turn, f"held_die_{position}", held)

        update_fields = [f"held_die_{position}" for position in range(1, 6)]
        turn.save(update_fields=update_fields)

        response: dict[str, object] = {
            "turn_id": turn.pk,
            "held_dice": list(turn.held_dice),
            "can_roll": True,
        }

        transaction.on_commit(
            lambda: publisher(
                "table_changed",
                {"game_id": game_id, "turn_id": turn.pk},
            )
        )

        return response


def _lock_current_turn(game_id: int) -> Turn:
    if not Game.objects.filter(pk=game_id).exists():
        raise GameNotFound

    turn = (
        Turn.objects.select_for_update()
        .select_related(
            "game_participant__tournament_participant__player_profile__user",
            "game_participant__game__round__tournament",
        )
        .filter(
            game_participant__game_id=game_id,
            completed_at__isnull=True,
        )
        .order_by("game_participant__turn_order", "number", "pk")
        .first()
    )

    if turn is None:
        raise HoldUnavailable

    return turn


def _require_legal_hold(turn: Turn, user: User) -> None:
    participant = turn.game_participant
    owner = participant.tournament_participant.player_profile.user
    tournament = participant.game.round.tournament

    if owner.pk != user.pk:
        raise HoldForbidden

    if tournament.status != TournamentStatus.ACTIVE:
        raise HoldUnavailable

    if hasattr(turn, "score_entry"):
        raise HoldUnavailable

    roll_count = turn.rolls.count()

    if roll_count == 0 or roll_count >= 3:
        raise HoldUnavailable
