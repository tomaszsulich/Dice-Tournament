from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.tests.factories import PlayerProfileFactory, UserFactory
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentParticipant
from tournaments.services.participants import (
    AlreadyRegistered,
    ParticipationNotFound,
    PlayerProfileRequired,
    RegistrationUnavailable,
    SelfWithdrawalUnavailable,
    TournamentFull,
    join_tournament,
    leave_tournament,
)


def build_tournament(**overrides):
    values = {
        "name": "Registration Tournament",
        "status": TournamentStatus.REGISTRATION,
        "registration_mode": RegistrationMode.OPEN,
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


@pytest.mark.django_db
def test_join_open_registration_creates_participant_with_identity_snapshot():
    tournament = build_tournament()

    profile = PlayerProfileFactory.create(
        user__first_name="Jan",
        user__last_name="Kowalski",
        display_name="Jan Kowalski",
        nickname="Kostka",
    )

    participant = join_tournament(tournament_id=tournament.pk, user=profile.user)

    assert participant.tournament == tournament
    assert participant.player_profile == profile
    assert participant.status == ParticipantStatus.REGISTERED
    assert participant.full_name_snapshot == "Jan Kowalski"
    assert participant.display_name_snapshot == "Jan Kowalski"
    assert participant.nickname_snapshot == "Kostka"


@pytest.mark.django_db
def test_join_requires_player_profile():
    tournament = build_tournament()
    user = UserFactory.create()

    with pytest.raises(PlayerProfileRequired):
        join_tournament(tournament_id=tournament.pk, user=user)


@pytest.mark.django_db
def test_join_rejects_organizer_only_registration():
    tournament = build_tournament(
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
    )

    profile = PlayerProfileFactory.create()

    with pytest.raises(RegistrationUnavailable):
        join_tournament(tournament_id=tournament.pk, user=profile.user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        TournamentStatus.DRAFT,
        TournamentStatus.ACTIVE,
        TournamentStatus.COMPLETED,
    ],
)
def test_join_rejects_invalid_tournament_status(status):
    tournament = build_tournament(status=status)
    profile = PlayerProfileFactory.create()

    with pytest.raises(RegistrationUnavailable):
        join_tournament(tournament_id=tournament.pk, user=profile.user)


@pytest.mark.django_db
def test_join_rejects_manually_closed_registration():
    tournament = build_tournament(
        registration_closed_at=timezone.now(),
    )

    profile = PlayerProfileFactory.create()

    with pytest.raises(RegistrationUnavailable):
        join_tournament(tournament_id=tournament.pk, user=profile.user)


@pytest.mark.django_db
def test_join_rejects_expired_registration_deadline():
    tournament = build_tournament(
        registration_deadline=timezone.now() - timedelta(minutes=1),
    )

    profile = PlayerProfileFactory.create()

    with pytest.raises(RegistrationUnavailable):
        join_tournament(tournament_id=tournament.pk, user=profile.user)


@pytest.mark.django_db
def test_join_rejects_full_tournament():
    tournament = build_tournament(max_participants=2)

    first_profile = PlayerProfileFactory.create()
    second_profile = PlayerProfileFactory.create()
    joining_profile = PlayerProfileFactory.create()

    TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=first_profile,
        full_name_snapshot="First Player",
        display_name_snapshot="First",
        nickname_snapshot="First",
        status=ParticipantStatus.REGISTERED,
    )

    TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=second_profile,
        full_name_snapshot="Second Player",
        display_name_snapshot="Second",
        nickname_snapshot="Second",
        status=ParticipantStatus.REGISTERED,
    )

    with pytest.raises(TournamentFull):
        join_tournament(tournament_id=tournament.pk, user=joining_profile.user)


@pytest.mark.django_db
def test_join_rejects_already_registered_participant():
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()

    join_tournament(tournament_id=tournament.pk, user=profile.user)

    with pytest.raises(AlreadyRegistered):
        join_tournament(tournament_id=tournament.pk, user=profile.user)


@pytest.mark.django_db
def test_join_reactivates_withdrawn_participant_without_replacing_record():
    tournament = build_tournament()

    profile = PlayerProfileFactory.create(
        user__first_name="Jan",
        user__last_name="Kowalski",
        display_name="Jan Kowalski",
        nickname="Kostka",
    )

    participant = join_tournament(tournament_id=tournament.pk, user=profile.user)
    old_joined_at = participant.joined_at
    old_pk = participant.pk

    old_snapshot = (
        participant.full_name_snapshot,
        participant.display_name_snapshot,
        participant.nickname_snapshot,
    )

    participant.status = ParticipantStatus.WITHDRAWN
    participant.withdrawn_at = timezone.now()
    participant.withdrawn_by = profile.user
    participant.withdrawal_reason = "Changed plans"

    participant.save(
        update_fields=(
            "status",
            "withdrawn_at",
            "withdrawn_by",
            "withdrawal_reason",
        )
    )

    profile.display_name = "Changed display name"
    profile.nickname = "ChangedNickname"
    profile.save(update_fields=("display_name", "nickname"))

    rejoined = join_tournament(tournament_id=tournament.pk, user=profile.user)

    assert rejoined.pk == old_pk
    assert rejoined.status == ParticipantStatus.REGISTERED
    assert rejoined.joined_at >= old_joined_at
    assert rejoined.withdrawn_at is None
    assert rejoined.withdrawn_by is None
    assert rejoined.withdrawal_reason == ""

    assert (
        rejoined.full_name_snapshot,
        rejoined.display_name_snapshot,
        rejoined.nickname_snapshot,
    ) == old_snapshot

    assert (
        TournamentParticipant.objects.filter(
            tournament=tournament,
            player_profile=profile,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_withdrawn_participant_does_not_occupy_registration_place():
    tournament = build_tournament(max_participants=2)

    withdrawn_profile = PlayerProfileFactory.create()
    registered_profile = PlayerProfileFactory.create()
    joining_profile = PlayerProfileFactory.create()

    TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=withdrawn_profile,
        full_name_snapshot="Withdrawn Player",
        display_name_snapshot="Withdrawn",
        nickname_snapshot="Withdrawn",
        status=ParticipantStatus.WITHDRAWN,
    )

    TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=registered_profile,
        full_name_snapshot="Registered Player",
        display_name_snapshot="Registered",
        nickname_snapshot="Registered",
        status=ParticipantStatus.REGISTERED,
    )

    participant = join_tournament(
        tournament_id=tournament.pk, user=joining_profile.user
    )

    assert participant.status == ParticipantStatus.REGISTERED


@pytest.mark.django_db
def test_leave_preserves_participant_as_withdrawn():
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()

    participant = join_tournament(tournament_id=tournament.pk, user=profile.user)
    left_participant = leave_tournament(tournament_id=tournament.pk, user=profile.user)

    assert left_participant.pk == participant.pk
    assert left_participant.status == ParticipantStatus.WITHDRAWN
    assert left_participant.withdrawn_at is not None
    assert left_participant.withdrawn_by == profile.user
    assert TournamentParticipant.objects.filter(pk=participant.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        TournamentStatus.ACTIVE,
        TournamentStatus.COMPLETED,
    ],
)
def test_leave_rejects_tournament_after_start(status):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()

    join_tournament(tournament_id=tournament.pk, user=profile.user)

    tournament.status = status
    tournament.save(update_fields=("status",))

    with pytest.raises(SelfWithdrawalUnavailable):
        leave_tournament(tournament_id=tournament.pk, user=profile.user)


@pytest.mark.django_db
def test_leave_rejects_missing_participation():
    tournament = build_tournament()
    profile = PlayerProfileFactory.create()

    with pytest.raises(ParticipationNotFound):
        leave_tournament(tournament_id=tournament.pk, user=profile.user)
