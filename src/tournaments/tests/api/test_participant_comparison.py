import re

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import PlayerProfileFactory, UserFactory
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
    Roll,
    Round,
    ScoreEntry,
    ScoreResultKind,
    Tournament,
    TournamentOrganizer,
    TournamentParticipant,
    Turn,
)
from tournaments.selectors.participant_comparison import (
    compare_participant,
    get_participant_history_page,
)

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


def _completed_tournament(organizer, profile, number, status="completed"):
    tournament = Tournament.objects.create(
        name=f"Cup {number}",
        status=TournamentStatus.COMPLETED,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
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
        assert item["tournament"]["timezone"] == "Europe/Warsaw"


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
    assert content.index(tournaments[4].name) < content.index(tournaments[3].name)
    assert content.index(tournaments[3].name) < content.index(tournaments[2].name)


def test_dashboard_context_preselects_available_tournament(comparison_setup):
    organizer, profile, tournaments = comparison_setup
    client = APIClient()
    client.force_authenticate(organizer)

    response = client.get(
        reverse("participant-comparison", args=(profile.pk,)),
        {"tournament_id": tournaments[0].pk},
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert f'data-initial-tournament-id="{tournaments[0].pk}"' in content

    assert re.search(
        rf'name="tournament_ids" value="{tournaments[0].pk}"\s+checked',
        content,
    )


def test_invalid_dashboard_context_leaves_tournament_selection_open(comparison_setup):
    organizer, profile, tournaments = comparison_setup
    unavailable = tournaments[0]

    TournamentOrganizer.objects.filter(
        tournament=unavailable,
        user=organizer,
    ).delete()

    client = APIClient()
    client.force_authenticate(organizer)

    response = client.get(
        reverse("participant-comparison", args=(profile.pk,)),
        {"tournament_id": unavailable.pk},
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "data-initial-tournament-id" not in content
    assert unavailable.name not in content


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


def test_history_serializes_full_roll_snapshots_holds_and_final_decision(
    comparison_setup,
):
    organizer, profile, tournaments = comparison_setup
    tournament = tournaments[0]

    game_participant = GameParticipant.objects.get(
        game__round__tournament=tournament,
        tournament_participant__player_profile=profile,
    )

    turn = Turn.objects.create(game_participant=game_participant, number=1)

    first = Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    second = Roll.objects.create(
        turn=turn,
        roll_number=2,
        die_1=1,
        die_2=6,
        die_3=3,
        die_4=5,
        die_5=2,
        held_die_1=True,
        held_die_3=True,
    )

    ScoreEntry.objects.create(
        turn=turn,
        game_participant=game_participant,
        category="chance",
        result_kind=ScoreResultKind.POINTS,
        value=17,
    )

    result = get_participant_history_page(
        actor=organizer,
        participant_id=profile.pk,
        tournament_id=tournament.pk,
        page_number=1,
    )

    assert result["pagination"] == {
        "page": 1,
        "pages": 1,
        "count": 2,
        "has_next": False,
    }

    first_item, second_item = result["items"]

    assert first_item["id"] == first.pk
    assert first_item["round_id"] == game_participant.game.round_id
    assert first_item["dice"] == [1, 2, 3, 4, 5]

    assert first_item["held_after_roll"] == [True, False, True, False, False]
    assert first_item["decision"] is None

    assert second_item["id"] == second.pk
    assert second_item["dice"] == [1, 6, 3, 5, 2]
    assert second_item["held_after_roll"] is None

    assert second_item["decision"] == {
        "category": "chance",
        "category_label": "Chance",
        "result_kind": "points",
        "result_label": "Points",
        "value": 17,
        "selected_at": second_item["decision"]["selected_at"],
        "first_roll_bonus_applied": False,
    }


def test_history_marks_first_roll_figure_bonus(comparison_setup):
    organizer, profile, tournaments = comparison_setup
    tournament = tournaments[0]

    game_participant = GameParticipant.objects.get(
        game__round__tournament=tournament,
        tournament_participant__player_profile=profile,
    )

    turn = Turn.objects.create(game_participant=game_participant, number=1)

    Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    ScoreEntry.objects.create(
        turn=turn,
        game_participant=game_participant,
        category="chance",
        result_kind=ScoreResultKind.POINTS,
        value=30,
    )

    result = get_participant_history_page(
        actor=organizer,
        participant_id=profile.pk,
        tournament_id=tournament.pk,
        page_number=1,
    )

    assert result["items"][0]["decision"]["first_roll_bonus_applied"] is True


def test_history_can_be_filtered_by_round_id(comparison_setup):
    organizer, profile, tournaments = comparison_setup
    tournament = tournaments[0]

    first_participant = GameParticipant.objects.get(
        game__round__tournament=tournament,
        tournament_participant__player_profile=profile,
    )

    first_turn = Turn.objects.create(game_participant=first_participant, number=1)

    Roll.objects.create(
        turn=first_turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    second_round = Round.objects.create(
        tournament=tournament,
        number=2,
        name="Round 2",
        status=RoundStatus.COMPLETED,
    )

    second_game = Game.objects.create(
        round=second_round,
        display_number=2,
        allocation_seed=999,
        allocation_cost=0,
    )

    second_participant = GameParticipant.objects.create(
        game=second_game,
        tournament_participant=first_participant.tournament_participant,
        turn_order=1,
        is_completed=True,
        raw_score=12,
        final_score=12,
    )

    second_turn = Turn.objects.create(game_participant=second_participant, number=1)

    second_roll = Roll.objects.create(
        turn=second_turn,
        roll_number=1,
        die_1=6,
        die_2=5,
        die_3=4,
        die_4=3,
        die_5=2,
    )

    result = get_participant_history_page(
        actor=organizer,
        participant_id=profile.pk,
        tournament_id=tournament.pk,
        page_number=1,
        round_id=second_round.pk,
    )

    assert result["pagination"]["count"] == 1
    assert result["items"][0]["id"] == second_roll.pk
    assert result["items"][0]["round_id"] == second_round.pk


def test_history_api_accepts_optional_round_id_and_rejects_invalid_value(
    comparison_setup,
):
    organizer, profile, tournaments = comparison_setup
    tournament = tournaments[0]
    round_ = tournament.rounds.get(number=1)

    game_participant = GameParticipant.objects.get(
        game__round=round_,
        tournament_participant__player_profile=profile,
    )

    turn = Turn.objects.create(game_participant=game_participant, number=1)

    roll = Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=2,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=6,
    )

    client = APIClient()
    client.force_authenticate(organizer)
    url = reverse("participant-comparison-history-api", args=(profile.pk,))

    response = client.get(
        url,
        {
            "tournament_id": tournament.pk,
            "round_id": round_.pk,
        },
    )

    assert response.status_code == 200
    assert response.data["pagination"]["count"] == 1
    assert response.data["items"][0]["id"] == roll.pk

    invalid = client.get(
        url,
        {
            "tournament_id": tournament.pk,
            "round_id": "not-an-id",
        },
    )

    assert invalid.status_code == 400
    assert invalid.data["code"] == "INVALID_COMPARISON"
