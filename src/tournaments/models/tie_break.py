from django.conf import settings
from django.db import models


class TieBreakDecision(models.Model):
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="tie_break_decisions",
    )

    round = models.ForeignKey(
        "tournaments.Round",
        on_delete=models.PROTECT,
        related_name="tie_break_decisions",
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tie_break_decisions",
    )

    candidate_participant_ids = models.JSONField()

    selected_participant = models.ForeignKey(
        "tournaments.TournamentParticipant",
        on_delete=models.PROTECT,
        related_name="tie_break_decisions",
    )

    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tournament} — tie-break #{self.pk}"
