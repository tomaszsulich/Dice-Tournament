from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from tournaments.models import IdempotencyRecord, Roll
from tournaments.tasks.maintenance import (
    cleanup_expired_idempotency_records,
    flush_expired_tokens,
)

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


@pytest.mark.django_db
def test_cleanup_expired_idempotency_records_only_deletes_technical_records(roll_setup):
    user, game, turn = roll_setup()

    roll = Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    old = IdempotencyRecord.objects.create(
        user=user,
        game=game,
        command="roll",
        key="old-key",
        fingerprint="a" * 64,
        response={"ok": True},
    )

    fresh = IdempotencyRecord.objects.create(
        user=user,
        game=game,
        command="roll",
        key="fresh-key",
        fingerprint="b" * 64,
        response={"ok": True},
    )

    IdempotencyRecord.objects.filter(pk=old.pk).update(
        created_at=timezone.now()
        - timedelta(hours=settings.IDEMPOTENCY_RETENTION_HOURS + 1)
    )

    deleted = cleanup_expired_idempotency_records.run()

    assert deleted == 1
    assert not IdempotencyRecord.objects.filter(pk=old.pk).exists()
    assert IdempotencyRecord.objects.filter(pk=fresh.pk).exists()
    assert Roll.objects.filter(pk=roll.pk).exists()


@pytest.mark.django_db
def test_flush_expired_tokens_uses_simplejwt_cleanup_command(monkeypatch):
    calls: list[tuple[str, int]] = []

    def fake_call_command(name: str, *, verbosity: int) -> None:
        calls.append((name, verbosity))

    monkeypatch.setattr(
        "tournaments.tasks.maintenance.call_command",
        fake_call_command,
    )

    flush_expired_tokens.run()

    assert calls == [("flushexpiredtokens", 0)]


@pytest.mark.django_db
def test_simplejwt_cleanup_command_removes_only_expired_tokens():
    expired = OutstandingToken.objects.create(
        jti="expired-token",
        token="expired",
        created_at=timezone.now() - timedelta(hours=2),
        expires_at=timezone.now() - timedelta(hours=1),
    )

    BlacklistedToken.objects.create(token=expired)

    active = OutstandingToken.objects.create(
        jti="active-token",
        token="active",
        created_at=timezone.now(),
        expires_at=timezone.now() + timedelta(hours=1),
    )

    flush_expired_tokens.run()

    assert not OutstandingToken.objects.filter(pk=expired.pk).exists()
    assert not BlacklistedToken.objects.filter(token_id=expired.pk).exists()
    assert OutstandingToken.objects.filter(pk=active.pk).exists()
