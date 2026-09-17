from django.conf import settings
from django.db import models


class IdempotencyRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tournament_idempotency_records",
    )

    game = models.ForeignKey(
        "tournaments.Game",
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )

    command = models.CharField(max_length=32)
    key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)
    response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "game", "command", "key"),
                name="unique_idempotency_key_per_user_game_command",
            ),
        ]
