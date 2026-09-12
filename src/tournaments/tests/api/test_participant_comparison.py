import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import PlayerProfileFactory, UserFactory
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import (
    EventMode,
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
)
from tournaments.selectors.participant_comparison import compare_participant


def _completed_tournament(organizer, profile, number, status="completed"):
    tournament = Tournament.objects.create(
        name=f"Cup {number}",
        status=TournamentStatus.COMPLETED,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=1,
        max_participants=4,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=2,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.REMOTE,
    )

    if status != TournamentStatus.COMPLETED:
        Tournament.objects.filter(pk=tournament.pk).update(status=status)
        tournament.refresh_from_db()

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    participation = TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Historical Player",
        display_name_snapshot=f"Player snapshot: {number}",
    )

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        name="Round 1",
        status=RoundStatus.COMPLETED,
    )

    game = Game.objects.create(
        round=round_,
        display_number=1,
        allocation_seed=number,
        allocation_cost=0,
    )

    GameParticipant.objects.create(
        game=game,
        tournament_participant=participation,
        turn_order=1,
        is_completed=True,
        raw_score=10 * number,
        final_score=10 * number,
    )

    return tournament


@pytest.fixture
def comparison_setup(db):
    organizer = UserFactory.create()
    profile = PlayerProfileFactory.create()

    tournaments = [
        _completed_tournament(organizer, profile, number) for number in range(1, 6)
    ]

    return organizer, profile, tournaments


@pytest.mark.parametrize("count", [1, 4])
def test_comparison_accepts_one_or_four_tournaments(comparison_setup, count):
    organizer, profile, tournaments = comparison_setup

    result = compare_participant(
        actor=organizer,
        participant_id=profile.pk,
        tournament_ids=[tournament.pk for tournament in tournaments[:count]],
    )

    assert len(result["comparisons"]) == count

    for item in result["comparisons"]:
        assert "round_average" in item
        assert "rounds_played" in item


@pytest.mark.parametrize("ids", [[], [1, 2, 3, 4, 5], [1, 1]])
def test_comparison_rejects_zero_five_and_duplicate_ids(comparison_setup, ids):
    organizer, profile, tournaments = comparison_setup

    actual_ids = (
        [tournament.pk for tournament in tournaments]
        if len(ids) == 5
        else ([tournaments[0].pk] * 2 if len(ids) == 2 else ids)
    )

    client = APIClient()
    client.force_authenticate(organizer)
    url = reverse("participant-comparison-api", args=(profile.pk,))

    response = client.get(url, {"tournament_ids": actual_ids})

    assert response.status_code == 400
    assert response.data["code"] == "INVALID_COMPARISON"


@pytest.mark.parametrize("status", ["active", "cancelled"])
def test_active_and_cancelled_tournament_are_rejected(comparison_setup, status):
    organizer, profile, tournaments = comparison_setup
    tournament = tournaments[0]
    Tournament.objects.filter(pk=tournament.pk).update(status=status)
    client = APIClient()
    client.force_authenticate(organizer)

    response = client.get(
        reverse("participant-comparison-api", args=(profile.pk,)),
        {"tournament_ids": [tournament.pk]},
    )

    assert response.status_code == 404


def test_options_hide_active_and_cancelled_tournaments(comparison_setup):
    organizer, profile, tournaments = comparison_setup
    Tournament.objects.filter(pk=tournaments[0].pk).update(status="active")
    Tournament.objects.filter(pk=tournaments[1].pk).update(status="cancelled")

    client = APIClient()
    client.force_authenticate(organizer)

    response = client.get(reverse("participant-comparison", args=(profile.pk,)))
    content = response.content.decode()

    assert response.status_code == 200
    assert tournaments[0].name not in content
    assert tournaments[1].name not in content
    assert tournaments[2].name in content
    assert content.index(tournaments[2].name) < content.index(tournaments[3].name)
    assert content.index(tournaments[3].name) < content.index(tournaments[4].name)


def test_missing_permission_for_one_of_four_rejects_whole_request(comparison_setup):
    organizer, profile, tournaments = comparison_setup

    TournamentOrganizer.objects.filter(
        tournament=tournaments[3], user=organizer
    ).delete()

    client = APIClient()
    client.force_authenticate(organizer)

    response = client.get(
        reverse("participant-comparison-api", args=(profile.pk,)),
        {"tournament_ids": [item.pk for item in tournaments[:4]]},
    )

    assert response.status_code == 404


def test_participant_and_foreign_organizer_cannot_use_idor(comparison_setup):
    _organizer, profile, tournaments = comparison_setup
    url = reverse("participant-comparison-api", args=(profile.pk,))
    client = APIClient()

    for actor in (profile.user, UserFactory.create()):
        client.force_authenticate(actor)
        response = client.get(url, {"tournament_ids": [tournaments[0].pk]})
        assert response.status_code == 404


def test_comparison_query_count_is_stable(comparison_setup, django_assert_num_queries):
    organizer, profile, tournaments = comparison_setup

    with django_assert_num_queries(3):
        result = compare_participant(
            actor=organizer,
            participant_id=profile.pk,
            tournament_ids=[item.pk for item in tournaments[:4]],
        )

    assert len(result["comparisons"]) == 4


def test_superuser_can_compare_and_archived_is_future_compatible(comparison_setup):
    _organizer, profile, tournaments = comparison_setup
    Tournament.objects.filter(pk=tournaments[0].pk).update(status="archived")
    admin = UserFactory.create(is_superuser=True, is_staff=True)

    result = compare_participant(
        actor=admin,
        participant_id=profile.pk,
        tournament_ids=[tournaments[0].pk],
    )

    assert result["comparisons"][0]["tournament"]["status"] == "archived"
