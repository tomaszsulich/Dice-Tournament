from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Roll(models.Model):
    turn = models.ForeignKey(
        "tournaments.Turn",
        on_delete=models.CASCADE,
        related_name="rolls",
    )

    roll_number = models.PositiveSmallIntegerField()

    die_1 = models.PositiveSmallIntegerField()
    die_2 = models.PositiveSmallIntegerField()
    die_3 = models.PositiveSmallIntegerField()
    die_4 = models.PositiveSmallIntegerField()
    die_5 = models.PositiveSmallIntegerField()

    held_die_1 = models.BooleanField(default=False)
    held_die_2 = models.BooleanField(default=False)
    held_die_3 = models.BooleanField(default=False)
    held_die_4 = models.BooleanField(default=False)
    held_die_5 = models.BooleanField(default=False)

    rolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(roll_number__gte=1, roll_number__lte=3),
                name="roll_number_between_1_and_3",
            ),
            *[
                models.CheckConstraint(
                    condition=Q(**{f"die_{position}__gte": 1})
                    & Q(**{f"die_{position}__lte": 6}),
                    name=f"roll_die_{position}_between_1_and_6",
                )
                for position in range(1, 6)
            ],
            models.CheckConstraint(
                condition=(
                    ~Q(roll_number=1)
                    | Q(
                        held_die_1=False,
                        held_die_2=False,
                        held_die_3=False,
                        held_die_4=False,
                        held_die_5=False,
                    )
                ),
                name="first_roll_has_no_held_dice",
            ),
            models.UniqueConstraint(
                fields=("turn", "roll_number"),
                name="unique_roll_number_per_turn",
            ),
        ]

    @property
    def values(self) -> tuple[int, int, int, int, int]:
        return (self.die_1, self.die_2, self.die_3, self.die_4, self.die_5)

    @property
    def held_after_roll(self) -> tuple[bool, bool, bool, bool, bool]:
        """Return the immutable hold state immediately after this roll."""
        return (
            self.held_die_1,
            self.held_die_2,
            self.held_die_3,
            self.held_die_4,
            self.held_die_5,
        )

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Accepted roll snapshots cannot be modified.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.turn} — roll {self.roll_number}"
