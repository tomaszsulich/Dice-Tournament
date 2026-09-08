import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import SessionFamily, User

SESSION_ABSOLUTE_LIFETIME = timedelta(hours=8)
SESSION_INACTIVITY_TIMEOUT = timedelta(minutes=30)


class Clock:
    def now(self):
        return timezone.now()


class SessionRejected(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def create_session_family(*, user: User, clock: Clock | None = None):
    now = (clock or Clock()).now()

    return SessionFamily.objects.create(
        user=user,
        created_at=now,
        absolute_expires_at=now + SESSION_ABSOLUTE_LIFETIME,
        last_activity_at=now,
    )


def validate_session_family(
    *, family_id: uuid.UUID, clock: Clock | None = None
) -> SessionFamily:
    now = (clock or Clock()).now()

    try:
        family = SessionFamily.objects.get(pk=family_id)
    except (SessionFamily.DoesNotExist, ValueError, TypeError) as exc:
        raise SessionRejected("SESSION_INVALID") from exc

    if family.revoked_at is not None:
        raise SessionRejected("SESSION_REVOKED")

    if now >= family.absolute_expires_at:
        raise SessionRejected("SESSION_EXPIRED")

    if now >= family.last_activity_at + SESSION_INACTIVITY_TIMEOUT:
        revoke_session_family(family=family, clock=clock)
        raise SessionRejected("SESSION_INACTIVE")

    return family


def record_activity(*, family_id: uuid.UUID, clock: Clock | None = None) -> None:
    now = (clock or Clock()).now()

    with transaction.atomic():
        family = SessionFamily.objects.select_for_update().filter(pk=family_id).first()

        if family is None or family.revoked_at is not None:
            return

        if now >= family.absolute_expires_at:
            return

        if now >= family.last_activity_at + SESSION_INACTIVITY_TIMEOUT:
            family.revoked_at = now
            family.save(update_fields=["revoked_at"])
            return

        family.last_activity_at = now
        family.save(update_fields=["last_activity_at"])


def revoke_session_family(*, family: SessionFamily, clock: Clock | None = None) -> None:
    if family.revoked_at is not None:
        return

    family.revoked_at = (clock or Clock()).now()
    family.save(update_fields=["revoked_at"])
