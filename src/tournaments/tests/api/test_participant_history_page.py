from pathlib import Path

import pytest
from django.http import Http404

from accounts.factories import PlayerProfileFactory, UserFactory
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import (
    EventMode,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Round, Tournament, TournamentParticipant
from tournaments.selectors.participant_comparison import get_own_history_options

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


def _tournament(name: str, status: str):
    return Tournament.objects.create(
        name=name,
        status=status,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.REMOTE,
    )


def test_own_history_lists_only_the_actors_completed_tournaments(db):
    profile = PlayerProfileFactory.create()
    completed = _tournament("Completed", TournamentStatus.COMPLETED)
    active = _tournament("Active", TournamentStatus.ACTIVE)
    foreign = _tournament("Foreign", TournamentStatus.COMPLETED)

    TournamentParticipant.objects.create(
        tournament=completed,
        player_profile=profile,
        display_name_snapshot="History Player",
    )

    TournamentParticipant.objects.create(
        tournament=active,
        player_profile=profile,
        display_name_snapshot="History Player",
    )

    TournamentParticipant.objects.create(
        tournament=foreign,
        player_profile=PlayerProfileFactory.create(),
        display_name_snapshot="Foreign Player",
    )

    round_ = Round.objects.create(
        tournament=completed,
        number=1,
        name="Round 1",
        status=RoundStatus.COMPLETED,
    )

    result = get_own_history_options(actor=profile.user)

    assert [item["tournament"]["id"] for item in result["tournaments"]] == [
        completed.pk
    ]

    assert result["tournaments"][0]["rounds"] == [
        {
            "round_id": round_.pk,
            "round_number": 1,
            "round_name": "Round 1",
        }
    ]


def test_own_history_requires_a_player_profile(db):
    with pytest.raises(Http404):
        get_own_history_options(actor=UserFactory.create())


def test_participant_history_page_uses_the_own_history_shell(api_client, db):
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(profile.user)

    response = api_client.get("/history/")

    assert response.status_code == 200
    assert b"My roll" in response.content
    assert b"own-history-data" in response.content
    assert b'name="tournament_ids"' not in response.content


def test_participant_history_page_returns_404_without_player_profile(api_client, db):
    organizer = UserFactory.create()
    api_client.force_authenticate(organizer)

    response = api_client.get("/history/")

    assert response.status_code == 404


def test_profile_actions_keep_hidden_links_out_of_layout():
    stylesheet = Path("src/accounts/static/accounts/css/auth.css").read_text(
        encoding="utf-8"
    )

    assert ".page-actions [hidden]" in stylesheet
    assert "display: none;" in stylesheet.split(".page-actions [hidden]", 1)[1]
