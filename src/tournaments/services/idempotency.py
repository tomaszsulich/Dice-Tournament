import hashlib
import json
from collections.abc import Mapping
from typing import Any

from tournaments.models import IdempotencyRecord

ROLL_COMMAND = "ROLL"


class IdempotencyConflict(Exception):
    code = "IDEMPOTENCY_CONFLICT"


def canonicalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload)


def hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()

    return hashlib.sha256(encoded).hexdigest()


def find_idempotency_record(*, user, game_id: int, key: str):
    return IdempotencyRecord.objects.filter(
        user=user,
        game_id=game_id,
        command=ROLL_COMMAND,
        key=key,
    ).first()


def replay_or_raise_conflict(
    record: IdempotencyRecord,
    fingerprint: str,
) -> dict[str, Any]:
    if record.fingerprint != fingerprint:
        raise IdempotencyConflict
    return record.response
