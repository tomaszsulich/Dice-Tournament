from django.core.exceptions import ValidationError
from django.utils import timezone

from tournaments.domain.tournament.types import TournamentStatus
from tournaments.models import Tournament


def open_registration(tournament: Tournament) -> Tournament:
    if tournament.status != TournamentStatus.DRAFT:
        raise ValidationError("Only a draft tournament can open registration.")

    tournament.full_clean()
    tournament.status = TournamentStatus.REGISTRATION
    tournament.save(update_fields=("status",))

    return tournament


def start_tournament(tournament: Tournament) -> Tournament:
    if tournament.status != TournamentStatus.REGISTRATION:
        raise ValidationError("Only a tournament in registration can be started.")

    tournament.full_clean()
    tournament.status = TournamentStatus.ACTIVE
    tournament.starts_at = timezone.now()
    tournament.save(update_fields=("status", "starts_at"))

    return tournament


def complete_tournament(tournament: Tournament) -> Tournament:
    if tournament.status != TournamentStatus.ACTIVE:
        raise ValidationError("Only an active tournament can be completed.")

    tournament.status = TournamentStatus.COMPLETED
    tournament.completed_at = timezone.now()
    tournament.save(update_fields=("status", "completed_at"))

    return tournament
