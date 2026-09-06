from collections.abc import Callable, Mapping
from typing import Any

from django.db import transaction

from accounts.models import User
from tournaments.domain.dice.randomizer import DiceRandomizer
from tournaments.domain.tournament.types import EventMode, TournamentStatus
from tournaments.models import Game, IdempotencyRecord, Roll, Turn
from tournaments.services.idempotency import (
    ROLL_COMMAND,
    canonicalize_payload,
    find_idempotency_record,
    hash_payload,
    replay_or_raise_conflict,
)

Publisher = Callable[[str, dict[str, int]], None]


class RollCommandError(Exception):
    code = "ROLL_COMMAND_ERROR"


class GameNotFound(RollCommandError):
    code = "GAME_NOT_FOUND"


class RollForbidden(RollCommandError):
    code = "ROLL_FORBIDDEN"


class RollUnavailable(RollCommandError):
    code = "ROLL_UNAVAILABLE"


class InvalidRollPayload(RollCommandError):
    code = "INVALID_ROLL_PAYLOAD"


def execute_roll(
    *,
    user: User,
    game_id: int,
    payload: Mapping[str, Any],
    key: str,
    rng: DiceRandomizer,
    publisher: Publisher,
) -> dict[str, Any]:
    """Execute one authoritative roll and make retries return the saved response."""
    if not getattr(user, "is_authenticated", False):
        raise RollForbidden

    canonical = canonicalize_payload(payload)
    fingerprint = hash_payload(canonical)

    existing = find_idempotency_record(user=user, game_id=game_id, key=key)

    if existing is not None:
        return replay_or_raise_conflict(existing, fingerprint)

    with transaction.atomic():
        turn = _lock_current_turn(game_id)
        existing = find_idempotency_record(user=user, game_id=game_id, key=key)

        if existing is not None:
            return replay_or_raise_conflict(existing, fingerprint)

        _require_legal_roll(turn, user)

        previous_roll = turn.rolls.order_by("roll_number").last()
        roll_number = 1 if previous_roll is None else previous_roll.roll_number + 1
        held_before = (False,) * 5 if previous_roll is None else turn.held_dice

        event_mode = turn.game_participant.game.round.tournament.event_mode

        values = _build_values(
            event_mode=event_mode,
            payload=canonical,
            previous_roll=previous_roll,
            held_before=held_before,
            rng=rng,
        )

        roll = _create_roll(
            turn=turn,
            roll_number=roll_number,
            values=values,
            held_before=held_before,
        )

        response = _serialize_roll(roll)

        IdempotencyRecord.objects.create(
            user=user,
            game_id=game_id,
            command=ROLL_COMMAND,
            key=key,
            fingerprint=fingerprint,
            response=response,
        )

        transaction.on_commit(
            lambda: publisher(
                "table_changed",
                {"game_id": game_id, "turn_id": turn.pk, "roll_id": roll.pk},
            )
        )

        return response


def _lock_current_turn(game_id: int) -> Turn:
    game_exists = Game.objects.filter(pk=game_id).exists()
    if not game_exists:
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
        raise RollUnavailable

    return turn


def _require_legal_roll(turn: Turn, user: User) -> None:
    tournament = turn.game_participant.game.round.tournament
    owner = turn.game_participant.tournament_participant.player_profile.user

    if owner.pk != user.pk:
        raise RollForbidden

    if tournament.status != TournamentStatus.ACTIVE:
        raise RollUnavailable

    if hasattr(turn, "score_entry"):
        raise RollUnavailable

    if turn.rolls.count() >= 3:
        raise RollUnavailable


def _build_values(
    *,
    event_mode: str,
    payload: Mapping[str, Any],
    previous_roll: Roll | None,
    held_before: tuple[bool, bool, bool, bool, bool],
    rng: DiceRandomizer,
) -> tuple[int, int, int, int, int]:
    if event_mode == EventMode.REMOTE:
        if payload:
            raise InvalidRollPayload

        previous_values = (
            previous_roll.values if previous_roll is not None else (0,) * 5
        )

        return tuple(
            previous_values[index] if held_before[index] else rng.randint(1, 6)
            for index in range(5)
        )

    if event_mode == EventMode.IN_PERSON:
        values = payload.get("values")

        if set(payload) != {"values"} or not _is_physical_snapshot(values):
            raise InvalidRollPayload

        snapshot = tuple(values)

        if previous_roll is not None:
            for index, held in enumerate(held_before):
                if held and snapshot[index] != previous_roll.values[index]:
                    raise InvalidRollPayload

        return snapshot
    raise InvalidRollPayload


def _is_physical_snapshot(value: Any) -> bool:
    return (
        isinstance(value, list | tuple)
        and len(value) == 5
        and all(type(die) is int and 1 <= die <= 6 for die in value)
    )


def _create_roll(
    *,
    turn: Turn,
    roll_number: int,
    values: tuple[int, int, int, int, int],
    held_before: tuple[bool, bool, bool, bool, bool],
) -> Roll:
    return Roll.objects.create(
        turn=turn,
        roll_number=roll_number,
        **{f"die_{index + 1}": value for index, value in enumerate(values)},
        **{f"held_die_{index + 1}": held for index, held in enumerate(held_before)},
    )


def _serialize_roll(roll: Roll) -> dict[str, Any]:
    return {
        "id": roll.pk,
        "turn_id": roll.turn_id,
        "roll_number": roll.roll_number,
        "values": list(roll.values),
        "held_before_roll": [
            roll.held_die_1,
            roll.held_die_2,
            roll.held_die_3,
            roll.held_die_4,
            roll.held_die_5,
        ],
    }
