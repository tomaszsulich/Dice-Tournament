from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from tournaments.domain.dice.categories import SCHOOL_CATEGORIES, ScoreCategory

CATEGORY_CHOICES = tuple((category.value, category.label) for category in ScoreCategory)
SCHOOL_CATEGORY_VALUES = frozenset(category.value for category in SCHOOL_CATEGORIES)


class ScoreResultKind(models.TextChoices):
    POINTS = "points", "Points"
    SCHOOL_BALANCE = "school_balance", "School balance"
    STRIKE_OFF = "strike_off", "Strike-off"


class ScoreEntry(models.Model):
    turn = models.OneToOneField(
        "tournaments.Turn",
        on_delete=models.CASCADE,
        related_name="score_entry",
    )

    game_participant = models.ForeignKey(
        "tournaments.GameParticipant",
        on_delete=models.CASCADE,
        related_name="score_entries",
    )

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    result_kind = models.CharField(max_length=20, choices=ScoreResultKind)
    value = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("game_participant", "category"),
                name="unique_score_category_per_game_participant",
            ),
            models.CheckConstraint(
                condition=(
                    Q(result_kind=ScoreResultKind.STRIKE_OFF, value__isnull=True)
                    | ~Q(result_kind=ScoreResultKind.STRIKE_OFF)
                    & Q(value__isnull=False)
                ),
                name="score_entry_value_matches_result_kind",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors = {}

        if self.turn_id and self.game_participant_id:
            turn_participant_id = self.turn.game_participant_id

            if turn_participant_id != self.game_participant_id:
                errors["game_participant"] = (
                    "Score entry must belong to the participant who owns the turn."
                )

        is_school = self.category in SCHOOL_CATEGORY_VALUES

        if is_school and self.result_kind != ScoreResultKind.SCHOOL_BALANCE:
            errors["result_kind"] = "School categories require a school balance."
        elif not is_school and self.result_kind == ScoreResultKind.SCHOOL_BALANCE:
            errors["result_kind"] = "Only school categories can store a school balance."

        if self.result_kind == ScoreResultKind.STRIKE_OFF and self.value is not None:
            errors["value"] = "A strike-off does not store a numeric value."
        elif self.result_kind != ScoreResultKind.STRIKE_OFF and self.value is None:
            errors["value"] = "A numeric scoring result requires a value."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.turn} — {self.get_category_display()}"
