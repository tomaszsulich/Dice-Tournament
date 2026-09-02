import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.tests.factories import UserFactory
from tournaments.domain.tournament.types import (
    EventMode,
    RegistrationMode,
)
from tournaments.models import Tournament, TournamentOrganizer
from tournaments.permissions import IsTournamentOrganizer


@pytest.fixture
def tournament(db):
    return Tournament.objects.create(
        name="Permission Tournament",
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=8,
        max_participants=32,
        timezone="Europe/Warsaw",
        group_rounds=5,
        table_size=4,
        event_mode=EventMode.IN_PERSON,
    )


def authenticated_request(user):
    raw_request = APIRequestFactory().get("/")
    force_authenticate(raw_request, user=user)

    request = Request(raw_request)
    request.user = user
    return request


def test_permission_allows_tournament_organizer(tournament):
    user = UserFactory.create()

    TournamentOrganizer.objects.create(
        tournament=tournament,
        user=user,
    )

    request = authenticated_request(user)
    permission = IsTournamentOrganizer()

    assert permission.has_object_permission(
        request,
        None,
        tournament,
    )


def test_permission_denies_non_organizer(tournament):
    user = UserFactory.create()

    request = authenticated_request(user)
    permission = IsTournamentOrganizer()

    assert not permission.has_object_permission(
        request,
        None,
        tournament,
    )


def test_permission_does_not_treat_staff_as_tournament_organizer(
    tournament,
):
    user = UserFactory.create(is_staff=True)

    request = authenticated_request(user)
    permission = IsTournamentOrganizer()

    assert not permission.has_object_permission(
        request,
        None,
        tournament,
    )
