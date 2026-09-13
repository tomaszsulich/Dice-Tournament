from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from tournaments.models import IdempotencyRecord


@shared_task
def cleanup_expired_idempotency_records() -> int:
    """Delete only expired technical idempotency records."""
    cutoff = timezone.now() - timedelta(hours=settings.IDEMPOTENCY_RETENTION_HOURS)
    deleted, _details = IdempotencyRecord.objects.filter(created_at__lt=cutoff).delete()
    return deleted


@shared_task
def flush_expired_tokens() -> None:
    """Remove expired JWT token records using SimpleJWT's supported command."""
    call_command("flushexpiredtokens", verbosity=0)
