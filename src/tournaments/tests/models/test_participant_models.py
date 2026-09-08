import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from accounts.models import PlayerProfile
from accounts.tests.factories import UserFactory
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantStatus,
    PokerScoringVariant,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentParticipant
from tournaments.services.participants import create_participant


def build_tournament(**overrides):
    values = {
        "name": "Participant Snapshot Tournament",
        "status": TournamentStatus.REGISTRATION,
        "min_participants": 2,
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


def build_profile(
    first_name="Jan",
    last_name="Kowalski",
    display_name="Jan Kowalski",
    nickname="DiceFox",
):
    user = UserFactory.create(
        first_name=first_name,
        last_name=last_name,
    )

    return PlayerProfile.objects.create(
        user=user,
        display_name=display_name,
        nickname=nickname,
    )


@pytest.mark.django_db
def test_create_participant_copies_identity_snapshot():
    tournament = build_tournament()
    profile = build_profile()

    participant = create_participant(
        tournament=tournament,
        player_profile=profile,
        starting_number=7,
        seeding=3,
    )

    assert participant.full_name_snapshot == "Jan Kowalski"
    assert participant.display_name_snapshot == "Jan Kowalski"
    assert participant.nickname_snapshot == "DiceFox"
    assert participant.starting_number == 7
    assert participant.seeding == 3
    assert participant.status == ParticipantStatus.REGISTERED


@pytest.mark.django_db
def test_profile_change_does_not_change_participant_snapshot():
    tournament = build_tournament()
    profile = build_profile()

    participant = create_participant(
        tournament=tournament,
        player_profile=profile,
    )

    profile.display_name = "New name"
    profile.nickname = "New nickname"
    profile.save(update_fields=("display_name", "nickname"))

    profile.user.first_name = "Adam"
    profile.user.last_name = "Nowak"
    profile.user.save(update_fields=("first_name", "last_name"))

    participant.refresh_from_db()

    assert participant.full_name_snapshot == "Jan Kowalski"
    assert participant.display_name_snapshot == "Jan Kowalski"
    assert participant.nickname_snapshot == "DiceFox"


@pytest.mark.django_db
def test_participant_identity_can_be_edited_before_start():
    tournament = build_tournament()
    profile = build_profile()
    participant = create_participant(
        tournament=tournament,
        player_profile=profile,
    )

    participant.display_name_snapshot = "Jan K."
    participant.nickname_snapshot = "New nickname"
    participant.starting_number = 12
    participant.seeding = 4

    participant.full_clean()
    participant.save()

    participant.refresh_from_db()

    assert participant.display_name_snapshot == "Jan K."
    assert participant.nickname_snapshot == "New nickname"
    assert participant.starting_number == 12
    assert participant.seeding == 4


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field_name", "new_value"),
    [
        ("full_name_snapshot", "Adam Nowak"),
        ("display_name_snapshot", "Adam"),
        ("nickname_snapshot", "NewNick"),
        ("starting_number", 99),
        ("seeding", 9),
    ],
)
def test_participant_identity_is_frozen_after_start(field_name, new_value):
    tournament = build_tournament(status=TournamentStatus.ACTIVE)
    profile = build_profile()

    participant = TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Jan Kowalski",
        display_name_snapshot="Jan Kowalski",
        nickname_snapshot="DiceFox",
        starting_number=7,
        seeding=3,
    )

    setattr(participant, field_name, new_value)

    with pytest.raises(ValidationError) as exc_info:
        participant.full_clean()

    assert field_name in exc_info.value.message_dict


@pytest.mark.django_db
def test_participant_status_can_change_after_start_without_deleting_history():
    tournament = build_tournament(status=TournamentStatus.ACTIVE)
    profile = build_profile()

    participant = TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Jan Kowalski",
        display_name_snapshot="Jan Kowalski",
        nickname_snapshot="DiceFox",
    )

    participant.status = ParticipantStatus.WITHDRAWN
    participant.full_clean()
    participant.save(update_fields=("status",))

    participant.refresh_from_db()

    assert participant.status == ParticipantStatus.WITHDRAWN
    assert participant.full_name_snapshot == "Jan Kowalski"
    assert TournamentParticipant.objects.filter(pk=participant.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_player_profile_can_participate_only_once_per_tournament():
    tournament = build_tournament()
    profile = build_profile()

    create_participant(
        tournament=tournament,
        player_profile=profile,
    )

    with pytest.raises(IntegrityError):
        TournamentParticipant.objects.create(
            tournament=tournament,
            player_profile=profile,
            full_name_snapshot="Jan Kowalski",
            display_name_snapshot="Jan Kowalski",
            nickname_snapshot="DiceFox",
        )


@pytest.mark.django_db
def test_tournament_exposes_participants_many_to_many_relation():
    tournament = build_tournament()
    profile = build_profile()

    create_participant(
        tournament=tournament,
        player_profile=profile,
    )

    assert list(tournament.participants.all()) == [profile]
    assert list(profile.tournaments.all()) == [tournament]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        ParticipantStatus.REGISTERED,
        ParticipantStatus.ACTIVE,
        ParticipantStatus.WITHDRAWN,
        ParticipantStatus.ELIMINATED,
    ],
)
def test_participant_accepts_canonical_statuses(status):
    tournament = build_tournament()
    profile = build_profile()

    participant = TournamentParticipant(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Jan Kowalski",
        display_name_snapshot="Jan Kowalski",
        nickname_snapshot="DiceFox",
        status=status,
    )

    participant.full_clean()


@pytest.mark.django_db
def test_participant_rejects_removed_status_from_old_plan():
    tournament = build_tournament()
    profile = build_profile()

    participant = TournamentParticipant(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Jan Kowalski",
        display_name_snapshot="Jan Kowalski",
        nickname_snapshot="DiceFox",
        status="removed",
    )

    with pytest.raises(ValidationError) as exc_info:
        participant.full_clean()

    assert "status" in exc_info.value.message_dict
