import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import PlayerProfile, User
from accounts.tests.factories import UserFactory
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantConnectionStatus,
    ParticipantStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import (
    Game,
    GameParticipant,
    Round,
    Tournament,
    TournamentOrganizer,
    TournamentParticipant,
    Turn,
)
from tournaments.selectors.organizer_dashboard import get_organizer_dashboard


def _dashboard_setup(table_count: int = 1):
    organizer = UserFactory.create()

    tournament = Tournament.objects.create(
        name="Command Cup",
        status=TournamentStatus.ACTIVE,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
        max_participants=128,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=2,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.REMOTE,
    )

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        name="Round 1",
        status=RoundStatus.ACTIVE,
    )

    users = User.objects.bulk_create(
        [
            User(username=f"dashboard-player-{number}")
            for number in range(1, table_count + 1)
        ]
    )

    profiles = PlayerProfile.objects.bulk_create(
        [
            PlayerProfile(
                user=user,
                display_name=f"Player {number}",
                nickname=f"player-{number}",
            )
            for number, user in enumerate(users, start=1)
        ]
    )

    for number, profile in enumerate(profiles, start=1):
        game = Game.objects.create(
            round=round_,
            display_number=number,
            allocation_seed=number,
            allocation_cost=0,
        )

        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            player_profile=profile,
            full_name_snapshot=f"Player {number}",
            display_name_snapshot=f"Player {number}",
            status=ParticipantStatus.ACTIVE,
            connection_status=ParticipantConnectionStatus.CONNECTED,
        )

        game_participant = GameParticipant.objects.create(
            game=game,
            tournament_participant=participant,
            turn_order=1,
        )

        Turn.objects.create(game_participant=game_participant, number=1)

    return organizer, tournament


@pytest.mark.django_db
def test_foreign_organizer_receives_404_and_guest_receives_no_data():
    _organizer, tournament = _dashboard_setup()
    client = APIClient()
    url = reverse("organizer-dashboard-api", args=(tournament.pk,))

    anonymous = client.get(url)
    client.force_authenticate(UserFactory.create())
    foreign = client.get(url)

    assert anonymous.status_code == 401
    assert foreign.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("table_count", [22, 64])
def test_all_active_tables_are_returned_without_pagination(table_count):
    organizer, tournament = _dashboard_setup(table_count)
    client = APIClient()
    client.force_authenticate(organizer)

    response = client.get(reverse("organizer-dashboard-api", args=(tournament.pk,)))

    assert response.status_code == 200
    assert len(response.data["tables"]) == table_count
    assert response.data["summary"]["tables"] == table_count

    assert "next" not in response.data
    assert "results" not in response.data


@pytest.mark.django_db
def test_table_38_attention_stays_in_global_queue():
    organizer, tournament = _dashboard_setup(38)

    TournamentParticipant.objects.filter(display_name_snapshot="Player 38").update(
        connection_status=ParticipantConnectionStatus.DISCONNECTED
    )

    snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert [item["display_number"] for item in snapshot["attention"]] == [38]
    assert snapshot["tables"][37]["requires_attention"] is True


@pytest.mark.django_db
def test_dashboard_query_count_is_stable_for_64_tables(django_assert_num_queries):
    organizer, tournament = _dashboard_setup(64)

    with django_assert_num_queries(6):
        snapshot = get_organizer_dashboard(
            actor=organizer,
            tournament_id=tournament.pk,
        )

    assert len(snapshot["tables"]) == 64


@pytest.mark.django_db
def test_dashboard_page_contains_one_detail_panel_and_one_global_queue():
    organizer, tournament = _dashboard_setup()
    client = APIClient()
    client.force_authenticate(organizer)

    response = client.get(reverse("organizer-dashboard", args=(tournament.pk,)))
    content = response.content.decode()

    assert response.status_code == 200
    assert content.count('id="table-detail"') == 1
    assert content.count('id="attention-list"') == 1
    assert "Incident" not in content
