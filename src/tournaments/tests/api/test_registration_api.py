from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.tests.factories import PlayerProfileFactory
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentParticipant


def build_tournament(**overrides):
    values = {
        "name": "Registration API Tournament",
        "status": TournamentStatus.REGISTRATION,
        "registration_mode": RegistrationMode.OPEN,
        "min_participants": 1,
        "max_participants": 16,
        "timezone": "Europe/Warsaw",
        "group_rounds": 5,
        "table_size": 4,
        "poker_scoring_variant": PokerScoringVariant.A,
        "event_mode": EventMode.IN_PERSON,
    }

    values.update(overrides)
    tournament = Tournament(**values)
    tournament.full_clean()
    tournament.save()

    return tournament


@pytest.mark.django_db
def test_open_registration_list_requires_authentication(api_client):
    response = api_client.get("/api/tournaments/?available_to_join=true")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_open_registration_list_returns_only_joinable_tournaments(api_client):
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)
    available = build_tournament(name="Available")

    build_tournament(
        name="Organizer only",
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
    )

    build_tournament(name="Active", status=TournamentStatus.ACTIVE)
    build_tournament(name="Closed", registration_closed_at=timezone.now())

    build_tournament(
        name="Expired",
        registration_deadline=timezone.now() - timedelta(minutes=1),
    )

    response = api_client.get("/api/tournaments/?available_to_join=true")

    assert response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in response.data] == [available.pk]
    assert response.data[0]["available_places"] == available.max_participants
    assert "tournament_participants" not in response.data[0]
    assert "participants" not in response.data[0]


@pytest.mark.django_db
def test_open_registration_list_excludes_full_tournament(api_client):
    viewer = PlayerProfileFactory.create()
    registered = PlayerProfileFactory.create()
    tournament = build_tournament(max_participants=1)

    TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=registered,
        full_name_snapshot="Registered Player",
        display_name_snapshot="Registered",
        nickname_snapshot="Registered",
        status=ParticipantStatus.REGISTERED,
    )

    api_client.force_authenticate(user=viewer.user)
    response = api_client.get("/api/tournaments/?available_to_join=true")

    assert response.status_code == status.HTTP_200_OK
    assert response.data == []


@pytest.mark.django_db
def test_join_requires_authentication(api_client):
    tournament = build_tournament()

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_join_creates_participation_for_authenticated_user(api_client):
    tournament = build_tournament()

    profile = PlayerProfileFactory.create(
        user__first_name="Jan",
        user__last_name="Kowalski",
        display_name="Jan Kowalski",
        nickname="Kostka",
    )

    api_client.force_authenticate(user=profile.user)

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    participant = TournamentParticipant.objects.get(
        tournament=tournament,
        player_profile=profile,
    )

    assert response.data["id"] == participant.pk
    assert response.data["status"] == ParticipantStatus.REGISTERED


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("player_id", 999),
        ("starting_number", 1),
        ("start_number", 1),
        ("seeding", 1),
        ("team_id", 1),
        ("team_label", "Team A"),
        ("group_id", 1),
        ("table_id", 1),
        ("status", ParticipantStatus.ACTIVE),
        ("unexpected", "value"),
    ],
)
def test_join_rejects_every_client_controlled_field(api_client, field, value):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {field: value},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field in response.data

    assert not TournamentParticipant.objects.filter(
        tournament=tournament,
        player_profile=profile,
    ).exists()


@pytest.mark.django_db
def test_join_uses_request_identity_not_payload_identity(api_client):
    tournament = build_tournament()
    requester = PlayerProfileFactory.create()
    other = PlayerProfileFactory.create()
    api_client.force_authenticate(user=requester.user)

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {"player_id": other.pk},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not TournamentParticipant.objects.filter(tournament=tournament).exists()


@pytest.mark.django_db
def test_join_organizer_only_returns_403(api_client):
    tournament = build_tournament(
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
    )

    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "SELF_REGISTRATION_FORBIDDEN"


@pytest.mark.django_db
def test_join_missing_tournament_returns_404(api_client):
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)

    response = api_client.post(
        "/api/tournaments/999999/join/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["code"] == "TOURNAMENT_NOT_FOUND"


@pytest.mark.django_db
def test_duplicate_join_returns_409(api_client):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)

    first_response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    second_response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.data["code"] == "ALREADY_REGISTERED"


@pytest.mark.django_db
def test_full_tournament_join_returns_409(api_client):
    tournament = build_tournament(max_participants=1)
    registered = PlayerProfileFactory.create()
    joining = PlayerProfileFactory.create()

    TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=registered,
        full_name_snapshot="Registered Player",
        display_name_snapshot="Registered",
        nickname_snapshot="Registered",
        status=ParticipantStatus.REGISTERED,
    )

    api_client.force_authenticate(user=joining.user)

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "TOURNAMENT_FULL"


@pytest.mark.django_db
def test_leave_marks_own_participation_as_withdrawn(api_client):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)

    join_response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    leave_response = api_client.post(
        f"/api/tournaments/{tournament.pk}/leave/",
        {},
        format="json",
    )

    assert join_response.status_code == status.HTTP_201_CREATED
    assert leave_response.status_code == status.HTTP_200_OK
    assert leave_response.data["status"] == ParticipantStatus.WITHDRAWN

    participant = TournamentParticipant.objects.get(
        tournament=tournament,
        player_profile=profile,
    )

    assert participant.status == ParticipantStatus.WITHDRAWN


@pytest.mark.django_db
def test_leave_missing_participation_returns_404(api_client):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/leave/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["code"] == "PARTICIPATION_NOT_FOUND"


@pytest.mark.django_db
def test_leave_after_start_returns_409(api_client):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()
    api_client.force_authenticate(user=profile.user)

    join_response = api_client.post(
        f"/api/tournaments/{tournament.pk}/join/",
        {},
        format="json",
    )

    assert join_response.status_code == status.HTTP_201_CREATED

    tournament.status = TournamentStatus.ACTIVE
    tournament.save(update_fields=("status",))

    response = api_client.post(
        f"/api/tournaments/{tournament.pk}/leave/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "SELF_WITHDRAWAL_UNAVAILABLE"


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_two_concurrent_join_requests_for_last_place_yield_201_and_409():
    tournament = build_tournament(max_participants=1)
    first_profile = PlayerProfileFactory.create()
    second_profile = PlayerProfileFactory.create()
    barrier = Barrier(2)

    def send_join(user):
        close_old_connections()
        client = APIClient()
        client.force_authenticate(user=user)
        barrier.wait()

        try:
            response = client.post(
                f"/api/tournaments/{tournament.pk}/join/",
                {},
                format="json",
            )
            return response.status_code, response.data
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(send_join, first_profile.user)
        second_future = executor.submit(send_join, second_profile.user)
        results = [first_future.result(), second_future.result()]

    assert sorted(code for code, _data in results) == [
        status.HTTP_201_CREATED,
        status.HTTP_409_CONFLICT,
    ]

    conflict = next(data for code, data in results if code == status.HTTP_409_CONFLICT)
    assert conflict["code"] == "TOURNAMENT_FULL"

    assert (
        TournamentParticipant.objects.filter(
            tournament=tournament,
            status=ParticipantStatus.REGISTERED,
        ).count()
        == 1
    )
