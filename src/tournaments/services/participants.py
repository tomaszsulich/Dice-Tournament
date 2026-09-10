from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import PlayerProfile, User
from tournaments.domain.tournament.types import (
    ParticipantStatus,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentParticipant


class TournamentRegistrationError(Exception):
    code = "TOURNAMENT_REGISTRATION_ERROR"


class PlayerProfileRequired(TournamentRegistrationError):
    code = "PLAYER_PROFILE_REQUIRED"


class RegistrationUnavailable(TournamentRegistrationError):
    code = "REGISTRATION_UNAVAILABLE"


class SelfRegistrationForbidden(RegistrationUnavailable):
    code = "SELF_REGISTRATION_FORBIDDEN"


class AlreadyRegistered(TournamentRegistrationError):
    code = "ALREADY_REGISTERED"


class TournamentFull(TournamentRegistrationError):
    code = "TOURNAMENT_FULL"


class SelfWithdrawalUnavailable(TournamentRegistrationError):
    code = "SELF_WITHDRAWAL_UNAVAILABLE"


class ParticipationNotFound(TournamentRegistrationError):
    code = "PARTICIPATION_NOT_FOUND"


def build_full_name_snapshot(player_profile: PlayerProfile) -> str:
    user = player_profile.user
    full_name = user.get_full_name().strip()
    return full_name or user.get_username()


def create_participant(
    tournament: Tournament,
    player_profile: PlayerProfile,
    team_label: str = "",
    starting_number: int | None = None,
    seeding: int | None = None,
) -> TournamentParticipant:
    if tournament.status not in {
        TournamentStatus.DRAFT,
        TournamentStatus.REGISTRATION,
    }:
        raise ValidationError("Participants cannot be added after tournament start.")

    participant = TournamentParticipant(
        tournament=tournament,
        player_profile=player_profile,
        full_name_snapshot=build_full_name_snapshot(player_profile),
        display_name_snapshot=player_profile.display_name,
        nickname_snapshot=player_profile.nickname,
        team_label=team_label,
        starting_number=starting_number,
        seeding=seeding,
    )

    participant.full_clean()
    participant.save()
    return participant


def _get_player_profile(user: User) -> PlayerProfile:
    try:
        return user.player_profile
    except PlayerProfile.DoesNotExist as exc:
        raise PlayerProfileRequired from exc


def _validate_self_registration(tournament: Tournament) -> None:
    now = timezone.now()

    if tournament.registration_mode != RegistrationMode.OPEN:
        raise SelfRegistrationForbidden

    if tournament.status != TournamentStatus.REGISTRATION:
        raise RegistrationUnavailable

    if tournament.registration_closed_at is not None:
        raise RegistrationUnavailable

    if (
        tournament.registration_deadline is not None
        and tournament.registration_deadline <= now
    ):
        raise RegistrationUnavailable


def _occupied_places(tournament: Tournament) -> int:
    return tournament.tournament_participants.filter(
        status=ParticipantStatus.REGISTERED
    ).count()


@transaction.atomic
def join_tournament(*, tournament_id: int, user: User) -> TournamentParticipant:
    player_profile = _get_player_profile(user)

    tournament = Tournament.objects.select_for_update().get(pk=tournament_id)
    _validate_self_registration(tournament)

    participant = TournamentParticipant.objects.filter(
        tournament=tournament,
        player_profile=player_profile,
    ).first()

    if participant is not None and participant.status != ParticipantStatus.WITHDRAWN:
        raise AlreadyRegistered

    if _occupied_places(tournament) >= tournament.max_participants:
        raise TournamentFull

    if participant is None:
        return create_participant(
            tournament=tournament,
            player_profile=player_profile,
        )

    participant.status = ParticipantStatus.REGISTERED
    participant.joined_at = timezone.now()

    participant.withdrawn_at = None
    participant.withdrawn_by = None
    participant.withdrawal_reason = ""
    participant.full_clean()

    participant.save(
        update_fields=[
            "status",
            "joined_at",
            "withdrawn_at",
            "withdrawn_by",
            "withdrawal_reason",
        ]
    )

    return participant


@transaction.atomic
def leave_tournament(*, tournament_id: int, user: User) -> TournamentParticipant:
    player_profile = _get_player_profile(user)

    tournament = Tournament.objects.select_for_update().get(pk=tournament_id)

    if tournament.status not in {
        TournamentStatus.DRAFT,
        TournamentStatus.REGISTRATION,
    }:
        raise SelfWithdrawalUnavailable

    participant = TournamentParticipant.objects.filter(
        tournament=tournament,
        player_profile=player_profile,
    ).first()

    if participant is None or participant.status == ParticipantStatus.WITHDRAWN:
        raise ParticipationNotFound

    participant.status = ParticipantStatus.WITHDRAWN
    participant.withdrawn_at = timezone.now()

    participant.withdrawn_by = user
    participant.withdrawal_reason = ""
    participant.full_clean()

    participant.save(
        update_fields=[
            "status",
            "withdrawn_at",
            "withdrawn_by",
            "withdrawal_reason",
        ]
    )

    return participant


@transaction.atomic
def add_participant_by_organizer(
    *,
    tournament_id: int,
    player_profile: PlayerProfile,
    team_label: str = "",
    starting_number: int | None = None,
    seeding: int | None = None,
) -> TournamentParticipant:
    tournament = Tournament.objects.select_for_update().get(pk=tournament_id)

    if tournament.status not in {TournamentStatus.DRAFT, TournamentStatus.REGISTRATION}:
        raise RegistrationUnavailable

    existing = TournamentParticipant.objects.filter(
        tournament=tournament,
        player_profile=player_profile,
    ).first()

    if existing is not None and existing.status != ParticipantStatus.WITHDRAWN:
        raise AlreadyRegistered

    if _occupied_places(tournament) >= tournament.max_participants:
        raise TournamentFull

    if existing is None:
        return create_participant(
            tournament=tournament,
            player_profile=player_profile,
            team_label=team_label,
            starting_number=starting_number,
            seeding=seeding,
        )

    existing.status = ParticipantStatus.REGISTERED
    existing.joined_at = timezone.now()

    existing.withdrawn_at = None
    existing.withdrawn_by = None
    existing.withdrawal_reason = ""

    existing.team_label = team_label
    existing.starting_number = starting_number
    existing.seeding = seeding

    existing.full_clean()
    existing.save()

    return existing
