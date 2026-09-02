from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from tournaments.domain.tournament.types import (
    DecisionTimeLimit,
    EventMode,
    RegistrationMode,
    TournamentStatus,
)

MAX_TOURNAMENT_PARTICIPANTS = 128
MIN_TABLE_SIZE = 2
MAX_TABLE_SIZE = 6

FROZEN_CONFIGURATION_FIELDS = (
    "min_participants",
    "max_participants",
    "group_rounds",
    "table_size",
    "decision_time_limit",
    "event_mode",
)


def validate_iana_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError("Enter a valid IANA time zone.") from exc


class Tournament(models.Model):
    name = models.CharField(max_length=150)

    status = models.CharField(
        max_length=20,
        choices=TournamentStatus,
        default=TournamentStatus.DRAFT,
    )

    registration_mode = models.CharField(
        max_length=20,
        choices=RegistrationMode,
        default=RegistrationMode.ORGANIZER_ONLY,
    )

    min_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    max_participants = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(MAX_TOURNAMENT_PARTICIPANTS),
        ],
    )

    registration_deadline = models.DateTimeField(null=True, blank=True)
    registration_closed_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    timezone = models.CharField(
        max_length=64,
        validators=[validate_iana_timezone],
    )

    group_rounds = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(2)],
    )

    table_size = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_TABLE_SIZE),
            MaxValueValidator(MAX_TABLE_SIZE),
        ],
    )

    decision_time_limit = models.PositiveSmallIntegerField(
        choices=DecisionTimeLimit,
        default=DecisionTimeLimit.UNLIMITED,
    )

    event_mode = models.CharField(
        max_length=20,
        choices=EventMode,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self) -> None:
        super().clean()

        errors = {}

        if (
            self.min_participants is not None
            and self.max_participants is not None
            and self.min_participants > self.max_participants
        ):
            errors["min_participants"] = (
                "Minimum participants cannot exceed maximum participants."
            )

        if (
            self.max_participants is not None
            and self.max_participants > MAX_TOURNAMENT_PARTICIPANTS
        ):
            errors["max_participants"] = (
                "Tournament cannot have more than 128 participants."
            )

        errors.update(self._frozen_configuration_errors())

        if errors:
            raise ValidationError(errors)

    def _frozen_configuration_errors(self) -> dict[str, str]:
        if not self.pk:
            return {}

        previous = type(self).objects.filter(pk=self.pk).first()

        if previous is None:
            return {}

        if previous.status not in {
            TournamentStatus.ACTIVE,
            TournamentStatus.COMPLETED,
        }:
            return {}

        errors = {}

        for field_name in FROZEN_CONFIGURATION_FIELDS:
            if getattr(self, field_name) != getattr(previous, field_name):
                errors[field_name] = (
                    "Tournament configuration cannot be changed after start."
                )

        return errors

    def __str__(self):
        return self.name


class TournamentOrganizer(models.Model):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="tournament_organizers",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tournament_organizer_roles",
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("tournament", "user"),
                name="unique_tournament_organizer",
            ),
        ]

    def __str__(self):
        return f"{self.tournament} — {self.user}"
