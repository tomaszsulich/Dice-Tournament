import pytest

from accounts.models import User
from tournaments.demo_builders import DemoWorldBuilder
from tournaments.models import Tournament
from tournaments.selectors.organizer_dashboard import get_organizer_dashboard

pytestmark = [pytest.mark.integration, pytest.mark.postgres]

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "size",
    [16, pytest.param(128, marks=pytest.mark.slow)],
)
def test_dashboard_query_count_does_not_grow_with_participant_scale(
    size,
    django_assert_num_queries,
    settings,
):
    settings.PASSWORD_HASHERS = FAST_HASHERS

    world = DemoWorldBuilder(
        size=size,
        scenario="active-round",
        seed=20260831,
        password="local-test-password",
    ).build()

    organizer = User.objects.get(username=world.organizer_username)
    tournament = Tournament.objects.get(pk=world.tournament_id)

    with django_assert_num_queries(6):
        snapshot = get_organizer_dashboard(
            actor=organizer,
            tournament_id=tournament.pk,
        )

    assert snapshot["summary"]["tables"] == size // 4
    assert len(snapshot["tables"]) == size // 4
