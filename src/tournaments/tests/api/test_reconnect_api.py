import pytest
from rest_framework import status

from accounts.jwt import SessionTokenObtainPairSerializer
from accounts.tests.factories import UserFactory
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import ParticipantStatus
from tournaments.models import (
    Game,
    GameParticipant,
    Round,
    TournamentOrganizer,
    TournamentParticipant,
    Turn,
)
from tournaments.services.connection_state import decision_deadline_for


@pytest.mark.django_db
def test_old_table_snapshot_returns_only_server_assigned_target(api_client, roll_setup):
    user, first_game, _turn = roll_setup()
    participant = TournamentParticipant.objects.get(player_profile__user=user)

    first_game.round.status = RoundStatus.COMPLETED
    first_game.round.save(update_fields=("status",))

    next_round = Round.objects.create(
        tournament=first_game.round.tournament,
        number=2,
        status=RoundStatus.ACTIVE,
    )

    next_game = Game.objects.create(
        round=next_round,
        display_number=1,
        allocation_seed=2,
        allocation_cost=0,
    )

    next_game_participant = GameParticipant.objects.create(
        game=next_game,
        tournament_participant=participant,
        turn_order=1,
    )

    Turn.objects.create(
        game_participant=next_game_participant,
        number=1,
        action_deadline=decision_deadline_for(first_game.round.tournament),
    )

    api_client.force_authenticate(user=user)

    old_response = api_client.get(f"/api/games/{first_game.pk}/state/")
    target_response = api_client.get(f"/api/games/{next_game.pk}/state/")

    assert old_response.status_code == status.HTTP_409_CONFLICT

    assert old_response.data == {
        "code": "TABLE_ASSIGNMENT_CHANGED",
        "table_id": next_game.pk,
        "target_url": f"/tables/{next_game.pk}/",
    }

    assert target_response.status_code == status.HTTP_200_OK
    assert target_response.data["game_id"] == next_game.pk


@pytest.mark.django_db
def test_inactive_participant_cannot_restore_gameplay_snapshot(api_client, roll_setup):
    user, game, _turn = roll_setup()
    participant = TournamentParticipant.objects.get(player_profile__user=user)
    participant.status = ParticipantStatus.WITHDRAWN
    participant.save(update_fields=("status",))

    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/games/{game.pk}/state/")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "PARTICIPATION_INACTIVE"


@pytest.mark.django_db
def test_old_table_page_redirects_participant_to_server_assigned_table(
    api_client, roll_setup
):
    user, first_game, _turn = roll_setup()
    participant = TournamentParticipant.objects.get(player_profile__user=user)

    first_game.round.status = RoundStatus.COMPLETED
    first_game.round.save(update_fields=("status",))

    next_round = Round.objects.create(
        tournament=first_game.round.tournament,
        number=2,
        status=RoundStatus.ACTIVE,
    )

    next_game = Game.objects.create(
        round=next_round,
        display_number=1,
        allocation_seed=2,
        allocation_cost=0,
    )

    GameParticipant.objects.create(
        game=next_game,
        tournament_participant=participant,
        turn_order=1,
    )

    api_client.force_authenticate(user=user)
    response = api_client.get(f"/tables/{first_game.pk}/")

    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == f"/tables/{next_game.pk}/"


@pytest.mark.django_db
def test_organizer_without_participation_cannot_open_participant_table(
    api_client, roll_setup
):
    _participant_user, game, _turn = roll_setup()
    organizer = UserFactory.create()

    TournamentOrganizer.objects.create(
        tournament=game.round.tournament,
        user=organizer,
    )

    api_client.force_authenticate(user=organizer)

    response = api_client.get(f"/tables/{game.pk}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_active_participant_profile_page_redirects_to_official_table(
    client,
    roll_setup,
):
    user, game, _turn = roll_setup()
    refresh = SessionTokenObtainPairSerializer.get_token(user)
    client.cookies["access_token"] = str(refresh.access_token)

    response = client.get("/profile/")

    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == f"/tables/{game.pk}/"


@pytest.mark.django_db
def test_active_participant_cannot_edit_profile_through_api(api_client, roll_setup):
    user, game, _turn = roll_setup()
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        "/api/profile/",
        {"display_name": "Changed during game"},
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {
        "code": "ACTIVE_GAME_IN_PROGRESS",
        "message": "Finish your active game before changing account details.",
        "details": {
            "table_id": game.pk,
            "target_url": f"/tables/{game.pk}/",
        },
    }


@pytest.mark.django_db
def test_active_participant_cannot_change_password_through_api(
    api_client,
    roll_setup,
):
    user, game, _turn = roll_setup()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        "/api/auth/users/set-password/",
        {
            "current_password": "test-password",
            "new_password": "Different-Password-42",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "ACTIVE_GAME_IN_PROGRESS"
    assert response.data["details"] == {
        "table_id": game.pk,
        "target_url": f"/tables/{game.pk}/",
    }
