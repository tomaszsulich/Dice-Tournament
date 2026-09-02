import pytest

from accounts.models import PlayerProfile
from accounts.tests.factories import UserFactory
from tournaments.domain.tournament.types import (
    EventMode,
    PokerScoringVariant,
    TournamentStatus,
)
from tournaments.models import Tournament
from tournaments.serializers.participants import (
    TournamentParticipantSerializer,
)
from tournaments.services.participants import create_participant


@pytest.mark.django_db
def test_participant_serializer_uses_historical_snapshot():
    user = UserFactory.create(
        first_name="Jan",
        last_name="Kowalski",
    )

    profile = PlayerProfile.objects.create(
        user=user,
        display_name="Jan Kowalski",
        nickname="Kostka",
    )

    tournament = Tournament.objects.create(
        name="Serializer Tournament",
        status=TournamentStatus.REGISTRATION,
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=5,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )

    participant = create_participant(
        tournament=tournament,
        player_profile=profile,
    )

    user.first_name = "Adam"
    user.last_name = "Nowak"
    user.save(update_fields=("first_name", "last_name"))

    profile.display_name = "Adam Nowak"
    profile.nickname = "NowyNick"
    profile.save(update_fields=("display_name", "nickname"))

    data = TournamentParticipantSerializer(participant).data

    assert data["full_name"] == "Jan Kowalski"
    assert data["display_name"] == "Jan Kowalski"
    assert data["nickname"] == "Kostka"
