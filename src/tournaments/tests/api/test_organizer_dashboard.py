import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import PlayerProfile, User
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

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


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


@pytest.mark.django_db
def test_waiting_and_completed_summary_counters_are_distinct_table_states():
    organizer, tournament = _dashboard_setup()
    game = Game.objects.get(round__tournament=tournament)

    game.game_participants.update(
        is_completed=True,
        raw_score=100,
        final_score=100,
    )

    waiting_snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert waiting_snapshot["tables"][0]["state"] == "waiting"
    assert waiting_snapshot["summary"]["waiting"] == 1
    assert waiting_snapshot["summary"]["completed"] == 0

    tournament.rounds.update(status=RoundStatus.COMPLETED)

    completed_snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert completed_snapshot["tables"][0]["state"] == "completed"
    assert completed_snapshot["summary"]["completed"] == 1
    assert completed_snapshot["summary"]["waiting"] == 0


@pytest.mark.django_db
def test_waiting_for_first_roll_keeps_the_phrase_together():
    organizer, tournament = _dashboard_setup()

    snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert snapshot["tables"][0]["last_action"] == (
        "Waiting for\u00a0the\u00a0first\u00a0roll"
    )


@pytest.mark.django_db
def test_completed_table_without_gameplay_has_neutral_last_action():
    organizer, tournament = _dashboard_setup()
    game = Game.objects.get(round__tournament=tournament)
    game.game_participants.update(is_completed=True)
    tournament.rounds.update(status=RoundStatus.COMPLETED)

    snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert snapshot["tables"][0]["last_action"] == "No\u00a0recorded\u00a0action"


@pytest.mark.django_db
def test_completed_dashboard_lists_profiles_for_comparison_navigation():
    organizer, tournament = _dashboard_setup(table_count=2)
    tournament.status = TournamentStatus.COMPLETED
    tournament.save(update_fields=("status",))

    snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert snapshot["comparison_participants"] == [
        {
            "profile_id": participant.player_profile_id,
            "display_name": participant.display_name_snapshot,
            "nickname": participant.nickname_snapshot,
        }
        for participant in tournament.tournament_participants.order_by(
            "starting_number",
            "display_name_snapshot",
            "pk",
        )
    ]


@pytest.mark.django_db
def test_active_dashboard_does_not_offer_comparison_navigation():
    organizer, tournament = _dashboard_setup()

    snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert snapshot["comparison_participants"] == []


@pytest.mark.django_db
def test_attention_queue_keeps_participant_name_together():
    organizer, tournament = _dashboard_setup()

    TournamentParticipant.objects.filter(tournament=tournament).update(
        display_name_snapshot="Jan Kowalski",
        connection_status=ParticipantConnectionStatus.DISCONNECTED,
    )

    snapshot = get_organizer_dashboard(
        actor=organizer,
        tournament_id=tournament.pk,
    )

    assert snapshot["attention"][0]["reasons"] == ["Disconnected: Jan\u00a0Kowalski"]
