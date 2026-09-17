from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from tournaments.domain.tournament.types import (
    ParticipantConnectionStatus,
    ParticipantStatus,
    TournamentStatus,
)

FROZEN_IDENTITY_FIELDS = (
    "full_name_snapshot",
    "display_name_snapshot",
    "nickname_snapshot",
    "starting_number",
    "seeding",
)


class TournamentParticipant(models.Model):
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="tournament_participants",
    )

    player_profile = models.ForeignKey(
        "accounts.PlayerProfile",
        on_delete=models.PROTECT,
        related_name="tournament_participations",
    )

    full_name_snapshot = models.CharField(max_length=301)
    display_name_snapshot = models.CharField(max_length=150)
    nickname_snapshot = models.CharField(max_length=50, blank=True)

    team_label = models.CharField(max_length=50, blank=True)

    starting_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    seeding = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    status = models.CharField(
        max_length=20,
        choices=ParticipantStatus,
        default=ParticipantStatus.REGISTERED,
    )

    connection_status = models.CharField(
        max_length=20,
        choices=ParticipantConnectionStatus,
        default=ParticipantConnectionStatus.DISCONNECTED,
    )

    disconnected_at = models.DateTimeField(null=True, blank=True)
    active_connection_channel = models.CharField(max_length=255, blank=True)

    joined_at = models.DateTimeField(default=timezone.now)

    withdrawn_at = models.DateTimeField(null=True, blank=True)

    withdrawn_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdrawn_tournament_participants",
    )

    withdrawal_reason = models.TextField(blank=True)

    total_score = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("tournament", "player_profile"),
                name="unique_tournament_participant",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors = self._frozen_identity_errors()

        if errors:
            raise ValidationError(errors)

    def _frozen_identity_errors(self) -> dict[str, str]:
        if not self.pk:
            return {}

        previous = (
            type(self).objects.select_related("tournament").filter(pk=self.pk).first()
        )

        if previous is None:
            return {}

        if previous.tournament.status not in {
            TournamentStatus.ACTIVE,
            TournamentStatus.COMPLETED,
        }:
            return {}

        errors = {}

        for field_name in FROZEN_IDENTITY_FIELDS:
            if getattr(self, field_name) != getattr(previous, field_name):
                errors[field_name] = (
                    "Participant identity cannot be changed after tournament start."
                )

        return errors

    def __str__(self):
        return f"{self.display_name_snapshot} — {self.tournament}"
