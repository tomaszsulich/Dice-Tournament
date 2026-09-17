from django.db import models

from tournaments.domain.tournament.rounds import RoundStatus, RoundType


class Round(models.Model):
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="rounds",
    )

    type = models.CharField(
        max_length=20,
        choices=RoundType,
        default=RoundType.GROUP,
    )

    number = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=150)

    status = models.CharField(
        max_length=20,
        choices=RoundStatus,
        default=RoundStatus.WAITING,
    )

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("tournament", "number"),
                name="unique_round_number_per_tournament",
            ),
        ]

    def __str__(self):
        return f"{self.tournament} — {self.name}"
