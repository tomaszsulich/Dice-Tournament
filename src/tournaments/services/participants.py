from django.core.exceptions import ValidationError

from accounts.models import PlayerProfile
from tournaments.domain.tournament.types import TournamentStatus
from tournaments.models import Tournament, TournamentParticipant


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
