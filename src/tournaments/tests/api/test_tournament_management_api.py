import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import PlayerProfileFactory, UserFactory
from tournaments.domain.tournament.types import (
    EventMode,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentOrganizer


def make_tournament(**overrides):
    values = {
        "name": "Managed tournament",
        "status": TournamentStatus.DRAFT,
        "registration_mode": RegistrationMode.ORGANIZER_ONLY,
        "min_participants": 2,
        "max_participants": 8,
        "timezone": "Europe/Warsaw",
        "group_rounds": 2,
        "table_size": 4,
        "poker_scoring_variant": PokerScoringVariant.A,
        "event_mode": EventMode.IN_PERSON,
    }
    values.update(overrides)

    return Tournament.objects.create(**values)


@pytest.mark.django_db
def test_authenticated_user_can_create_draft_and_becomes_organizer():
    user = UserFactory.create()
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("tournament-create"),
        {
            "name": "Managed tournament",
            "registration_mode": "organizer_only",
            "min_participants": 2,
            "max_participants": 8,
            "timezone": "Europe/Warsaw",
            "group_rounds": 2,
            "table_size": 4,
            "poker_scoring_variant": "a",
            "decision_time_limit": 0,
            "event_mode": "in_person",
        },
        format="json",
    )

    assert response.status_code == 201

    tournament = Tournament.objects.get(pk=response.data["id"])

    assert tournament.status == TournamentStatus.DRAFT
    assert TournamentOrganizer.objects.filter(tournament=tournament, user=user).exists()


@pytest.mark.django_db
def test_organizer_can_add_participant_in_organizer_only_mode():
    tournament = make_tournament(registration_mode=RegistrationMode.ORGANIZER_ONLY)
    organizer = UserFactory.create()

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    profile = PlayerProfileFactory.create()
    client = APIClient()
    client.force_authenticate(organizer)

    response = client.post(
        reverse("tournament-add-participant", args=[tournament.pk]),
        {"player_profile_id": profile.pk, "starting_number": 7, "seeding": 2},
        format="json",
    )

    assert response.status_code == 201

    participant = tournament.tournament_participants.get(player_profile=profile)

    assert participant.starting_number == 7
    assert participant.seeding == 2


@pytest.mark.django_db
def test_organizer_can_close_registration_before_deadline():
    tournament = make_tournament(status=TournamentStatus.REGISTRATION)
    organizer = UserFactory.create()

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    client = APIClient()
    client.force_authenticate(organizer)

    response = client.post(
        reverse("tournament-close-registration", args=[tournament.pk]),
        {},
        format="json",
    )

    assert response.status_code == 200
    tournament.refresh_from_db()
    assert tournament.registration_closed_at is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("team_label", "expected_status"),
    [
        ("A" * 50, 201),
        ("A" * 51, 400),
    ],
)
def test_organizer_participant_team_label_respects_50_character_limit(
    team_label,
    expected_status,
):
    tournament = make_tournament(registration_mode=RegistrationMode.ORGANIZER_ONLY)
    organizer = UserFactory.create()

    TournamentOrganizer.objects.create(tournament=tournament, user=organizer)

    profile = PlayerProfileFactory.create()
    client = APIClient()
    client.force_authenticate(organizer)

    response = client.post(
        reverse("tournament-add-participant", args=[tournament.pk]),
        {"player_profile_id": profile.pk, "team_label": team_label},
        format="json",
    )

    assert response.status_code == expected_status
