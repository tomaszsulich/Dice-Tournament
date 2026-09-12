from django.core.validators import MinValueValidator
from django.db import models


class Turn(models.Model):
    game_participant = models.ForeignKey(
        "tournaments.GameParticipant",
        on_delete=models.CASCADE,
        related_name="turns",
    )

    number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    held_die_1 = models.BooleanField(default=False)
    held_die_2 = models.BooleanField(default=False)
    held_die_3 = models.BooleanField(default=False)
    held_die_4 = models.BooleanField(default=False)
    held_die_5 = models.BooleanField(default=False)

    action_deadline = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("game_participant", "number"),
                name="unique_turn_number_per_game_participant",
            ),
        ]

    @property
    def held_dice(self) -> tuple[bool, bool, bool, bool, bool]:
        """Return the current mutable hold selection for this turn."""
        return (
            self.held_die_1,
            self.held_die_2,
            self.held_die_3,
            self.held_die_4,
            self.held_die_5,
        )

    def __str__(self):
        return f"{self.game_participant} — turn {self.number}"
