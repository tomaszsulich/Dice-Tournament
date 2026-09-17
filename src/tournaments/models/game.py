from django.core.validators import MinValueValidator
from django.db import models


class Game(models.Model):
    round = models.ForeignKey(
        "tournaments.Round",
        on_delete=models.CASCADE,
        related_name="games",
    )

    display_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    allocation_seed = models.BigIntegerField()
    allocation_cost = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    state_version = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("round", "display_number"),
                name="unique_game_display_number_per_round",
            ),
        ]

    @property
    def display_label(self) -> str:
        return f"Table #{self.display_number}"

    def __str__(self):
        return f"{self.round} — {self.display_label}"


class GameParticipant(models.Model):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="game_participants",
    )

    tournament_participant = models.ForeignKey(
        "tournaments.TournamentParticipant",
        on_delete=models.PROTECT,
        related_name="game_participations",
    )

    turn_order = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    is_completed = models.BooleanField(default=False)
    raw_score = models.IntegerField(default=0)
    school_balance = models.IntegerField(default=0)

    figure_points = models.IntegerField(default=0)
    bonus_points = models.IntegerField(default=0)
    final_score = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("game", "tournament_participant"),
                name="unique_participant_per_game",
            ),
            models.UniqueConstraint(
                fields=("game", "turn_order"),
                name="unique_turn_order_per_game",
            ),
        ]

    def __str__(self):
        return f"{self.game} — {self.tournament_participant}"
