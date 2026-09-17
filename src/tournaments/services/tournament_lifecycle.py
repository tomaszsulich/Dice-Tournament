from collections.abc import Callable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.table_sizes import compute_balanced_table_sizes
from tournaments.domain.tournament.types import ParticipantStatus, TournamentStatus
from tournaments.models import Tournament, TournamentOrganizer
from tournaments.services.round_barrier import create_initial_round

type Publisher = Callable[[str, dict[str, int]], None]


@transaction.atomic
def create_tournament(*, organizer: User, **configuration) -> Tournament:
    tournament = Tournament(**configuration)

    tournament.full_clean()
    tournament.save()
    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    return tournament


@transaction.atomic
def open_registration(tournament: Tournament) -> Tournament:
    tournament = Tournament.objects.select_for_update().get(pk=tournament.pk)

    if tournament.status != TournamentStatus.DRAFT:
        raise ValidationError("Only a draft tournament can open registration.")

    tournament.full_clean()
    tournament.status = TournamentStatus.REGISTRATION
    tournament.save(update_fields=("status",))

    return tournament


@transaction.atomic
def close_registration(tournament: Tournament) -> Tournament:
    tournament = Tournament.objects.select_for_update().get(pk=tournament.pk)

    if tournament.status != TournamentStatus.REGISTRATION:
        raise ValidationError("Only an open registration phase can be closed.")

    if tournament.registration_closed_at is None:
        tournament.registration_closed_at = timezone.now()
        tournament.save(update_fields=("registration_closed_at",))

    return tournament


@transaction.atomic
def start_tournament(
    tournament: Tournament,
    *,
    publisher: Publisher | None = None,
) -> Tournament:
    tournament = Tournament.objects.select_for_update().get(pk=tournament.pk)

    if tournament.status != TournamentStatus.REGISTRATION:
        raise ValidationError("Only a tournament in registration can be started.")

    registered = tournament.tournament_participants.filter(
        status=ParticipantStatus.REGISTERED
    )

    registered_count = registered.count()

    if registered_count < tournament.min_participants:
        raise ValidationError("Tournament does not have the minimum participant count.")

    if registered_count > tournament.max_participants:
        raise ValidationError("Tournament exceeds its participant limit.")

    try:
        compute_balanced_table_sizes(registered_count, tournament.table_size)
    except ValueError as exc:
        raise ValidationError(
            "The registered participant count cannot form a valid table structure."
        ) from exc

    tournament.full_clean()
    registered.update(status=ParticipantStatus.ACTIVE)
    tournament.status = TournamentStatus.ACTIVE
    tournament.starts_at = timezone.now()

    tournament.registration_closed_at = (
        tournament.registration_closed_at or timezone.now()
    )

    tournament.save(update_fields=("status", "starts_at", "registration_closed_at"))

    first_round = create_initial_round(tournament)

    if publisher is not None:
        transaction.on_commit(
            lambda: publisher("round_transition", {"round_id": first_round.pk})
        )

    return tournament


@transaction.atomic
def complete_tournament(tournament: Tournament) -> Tournament:
    tournament = Tournament.objects.select_for_update().get(pk=tournament.pk)

    if tournament.status != TournamentStatus.ACTIVE:
        raise ValidationError("Only an active tournament can be completed.")

    rounds = tournament.rounds.all()

    if rounds.filter(status__in=(RoundStatus.WAITING, RoundStatus.ACTIVE)).exists():
        raise ValidationError("Tournament still has unfinished rounds.")

    completed_group_rounds = rounds.filter(
        type="group",
        status=RoundStatus.COMPLETED,
    ).count()

    if completed_group_rounds < tournament.group_rounds:
        raise ValidationError("Tournament has not completed all required group rounds.")

    tournament.status = TournamentStatus.COMPLETED
    tournament.completed_at = timezone.now()
    tournament.save(update_fields=("status", "completed_at"))

    return tournament
