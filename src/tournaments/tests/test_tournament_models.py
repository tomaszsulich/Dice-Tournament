import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from accounts.tests.factories import UserFactory
from tournaments.domain.tournament.types import (
    EventMode,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentOrganizer


def build_tournament(**overrides):
    values = {
        "name": "Dice Tournament",
        "status": TournamentStatus.DRAFT,
        "registration_mode": RegistrationMode.ORGANIZER_ONLY,
        "min_participants": 8,
        "max_participants": 32,
        "timezone": "Europe/Warsaw",
        "group_rounds": 5,
        "table_size": 4,
        "event_mode": EventMode.IN_PERSON,
    }

    values.update(overrides)
    return Tournament(**values)


@pytest.mark.django_db
def test_tournament_accepts_valid_configuration():
    tournament = build_tournament()
    tournament.full_clean()


@pytest.mark.django_db
def test_tournament_accepts_128_max_participants():
    tournament = build_tournament(max_participants=128)
    tournament.full_clean()


@pytest.mark.django_db
def test_tournament_rejects_129_max_participants():
    tournament = build_tournament(max_participants=129)

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert "max_participants" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name",
    ["min_participants", "max_participants"],
)
def test_tournament_rejects_zero_participant_limits(field_name):
    tournament = build_tournament(**{field_name: 0})

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert field_name in exc_info.value.message_dict


@pytest.mark.django_db
def test_tournament_validation_handles_invalid_fields_independently():
    tournament = build_tournament(
        min_participants=-1,
        max_participants=129,
    )

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert "min_participants" in exc_info.value.message_dict
    assert "max_participants" in exc_info.value.message_dict


@pytest.mark.django_db
def test_tournament_rejects_minimum_above_maximum():
    tournament = build_tournament(
        min_participants=33,
        max_participants=32,
    )

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert "min_participants" in exc_info.value.message_dict


@pytest.mark.django_db
def test_tournament_accepts_minimum_independent_of_table_size():
    tournament = build_tournament(
        min_participants=10,
        max_participants=32,
        table_size=4,
    )

    tournament.full_clean()


@pytest.mark.django_db
def test_tournament_accepts_minimum_two_group_rounds():
    tournament = build_tournament(group_rounds=2)
    tournament.full_clean()


@pytest.mark.django_db
def test_tournament_rejects_single_group_round():
    tournament = build_tournament(group_rounds=1)

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert "group_rounds" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("table_size", [2, 3, 4, 5, 6])
def test_tournament_accepts_supported_table_sizes(table_size):
    tournament = build_tournament(table_size=table_size)
    tournament.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize("table_size", [1, 7])
def test_tournament_rejects_unsupported_table_sizes(table_size):
    tournament = build_tournament(table_size=table_size)

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert "table_size" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    "event_mode",
    [EventMode.IN_PERSON, EventMode.REMOTE],
)
def test_tournament_accepts_supported_event_modes(event_mode):
    tournament = build_tournament(event_mode=event_mode)
    tournament.full_clean()


@pytest.mark.django_db
def test_tournament_rejects_hybrid_event_mode():
    tournament = build_tournament(event_mode="hybrid")

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert "event_mode" in exc_info.value.message_dict


@pytest.mark.django_db
def test_tournament_rejects_invalid_timezone():
    tournament = build_tournament(timezone="Warsaw")

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert "timezone" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field_name", "new_value"),
    [
        ("min_participants", 10),
        ("max_participants", 64),
        ("group_rounds", 10),
        ("table_size", 6),
        ("decision_time_limit", 60),
        ("event_mode", EventMode.REMOTE),
    ],
)
def test_tournament_rejects_configuration_change_after_start(
    field_name,
    new_value,
):
    tournament = build_tournament(
        status=TournamentStatus.ACTIVE,
    )
    tournament.save()

    setattr(tournament, field_name, new_value)

    with pytest.raises(ValidationError) as exc_info:
        tournament.full_clean()

    assert field_name in exc_info.value.message_dict


@pytest.mark.django_db
def test_tournament_allows_configuration_change_before_start():
    tournament = build_tournament(
        status=TournamentStatus.REGISTRATION,
    )
    tournament.save()

    tournament.table_size = 6
    tournament.event_mode = EventMode.REMOTE
    tournament.full_clean()


@pytest.mark.django_db
def test_tournament_allows_multiple_organizers():
    tournament = build_tournament()
    tournament.save()

    first_user = UserFactory.create()
    second_user = UserFactory.create()

    TournamentOrganizer.objects.create(
        tournament=tournament,
        user=first_user,
    )

    TournamentOrganizer.objects.create(
        tournament=tournament,
        user=second_user,
    )

    assert tournament.tournament_organizers.count() == 2


@pytest.mark.django_db
def test_tournament_organizer_does_not_need_staff_status():
    tournament = build_tournament()
    tournament.save()
    user = UserFactory.create(is_staff=False)

    organizer = TournamentOrganizer.objects.create(
        tournament=tournament,
        user=user,
    )

    assert organizer.user == user
    assert user.is_staff is False


@pytest.mark.django_db(transaction=True)
def test_tournament_organizer_pair_must_be_unique():
    tournament = build_tournament()
    tournament.save()
    user = UserFactory.create()

    TournamentOrganizer.objects.create(
        tournament=tournament,
        user=user,
    )

    with pytest.raises(IntegrityError):
        TournamentOrganizer.objects.create(
            tournament=tournament,
            user=user,
        )
