import smtplib

import pytest
from django.db import transaction

from accounts.factories import PlayerProfileFactory
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament, TournamentParticipant
from tournaments.services.participants import add_participant_by_organizer
from tournaments.tasks import notifications


class FakeMailer:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, *, recipient: str, tournament_name: str) -> None:
        self.sent.append((recipient, tournament_name))


def build_tournament():
    return Tournament.objects.create(
        name="Celery Cup",
        status=TournamentStatus.REGISTRATION,
        registration_mode=RegistrationMode.ORGANIZER_ONLY,
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=3,
        table_size=4,
        poker_scoring_variant=PokerScoringVariant.A,
        event_mode=EventMode.IN_PERSON,
    )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_invitation_delivery_reloads_participant_and_uses_injected_mailer():
    tournament = build_tournament()
    profile = PlayerProfileFactory.create(user__email="player@example.com")

    participant = TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Player One",
        display_name_snapshot="Player One",
        status=ParticipantStatus.REGISTERED,
    )

    mailer = FakeMailer()

    delivered = notifications.deliver_tournament_invitation(
        participant.pk,
        mailer=mailer,
    )

    assert delivered is True
    assert mailer.sent == [("player@example.com", "Celery Cup")]


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_invitation_delivery_skips_no_longer_applicable_participant():
    tournament = build_tournament()
    profile = PlayerProfileFactory.create(user__email="")

    participant = TournamentParticipant.objects.create(
        tournament=tournament,
        player_profile=profile,
        full_name_snapshot="Player One",
        display_name_snapshot="Player One",
        status=ParticipantStatus.REGISTERED,
    )

    mailer = FakeMailer()

    assert (
        notifications.deliver_tournament_invitation(participant.pk, mailer=mailer)
        is False
    )

    participant.status = ParticipantStatus.WITHDRAWN
    participant.save(update_fields=("status",))
    profile.user.email = "player@example.com"
    profile.user.save(update_fields=("email",))

    assert (
        notifications.deliver_tournament_invitation(participant.pk, mailer=mailer)
        is False
    )

    participant.status = ParticipantStatus.REGISTERED
    participant.save(update_fields=("status",))
    tournament.status = TournamentStatus.ACTIVE
    tournament.save(update_fields=("status",))

    assert (
        notifications.deliver_tournament_invitation(participant.pk, mailer=mailer)
        is False
    )

    assert notifications.deliver_tournament_invitation(999999, mailer=mailer) is False
    assert mailer.sent == []


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_organizer_registration_enqueues_invitation_only_after_commit(monkeypatch):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create(user__email="player@example.com")
    queued: list[int] = []

    monkeypatch.setattr(
        notifications.send_tournament_invitation,
        "delay",
        lambda participant_id: queued.append(participant_id),
    )

    participant = add_participant_by_organizer(
        tournament_id=tournament.pk,
        player_profile=profile,
    )

    assert queued == [participant.pk]


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_organizer_registration_rollback_does_not_enqueue_invitation(monkeypatch):
    tournament = build_tournament()
    profile = PlayerProfileFactory.create(user__email="player@example.com")
    queued: list[int] = []

    monkeypatch.setattr(
        notifications.send_tournament_invitation,
        "delay",
        lambda participant_id: queued.append(participant_id),
    )

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            add_participant_by_organizer(
                tournament_id=tournament.pk,
                player_profile=profile,
            )
            raise RuntimeError("rollback")

    assert queued == []

    assert not TournamentParticipant.objects.filter(
        tournament=tournament,
        player_profile=profile,
    ).exists()


@pytest.mark.unit
def test_invitation_task_retries_retryable_smtp_failure(monkeypatch):
    class RetryRaised(Exception):
        pass

    error = smtplib.SMTPServerDisconnected("temporary failure")
    captured: dict[str, object] = {}

    def fail_delivery(participant_id: int) -> bool:
        raise error

    def fake_retry(*, exc, countdown):
        captured["exc"] = exc
        captured["countdown"] = countdown
        raise RetryRaised

    monkeypatch.setattr(notifications, "deliver_tournament_invitation", fail_delivery)
    monkeypatch.setattr(notifications.send_tournament_invitation, "retry", fake_retry)

    with pytest.raises(RetryRaised):
        notifications.send_tournament_invitation.run(123)

    assert captured == {"exc": error, "countdown": 2}
    assert notifications.send_tournament_invitation.max_retries == 3


@pytest.mark.unit
def test_invitation_task_retries_transient_smtp_response(monkeypatch):
    class RetryRaised(Exception):
        pass

    error = smtplib.SMTPDataError(451, b"try again later")
    captured: dict[str, object] = {}

    def fail_delivery(participant_id: int) -> bool:
        raise error

    def fake_retry(*, exc, countdown):
        captured["exc"] = exc
        captured["countdown"] = countdown
        raise RetryRaised

    monkeypatch.setattr(notifications, "deliver_tournament_invitation", fail_delivery)
    monkeypatch.setattr(notifications.send_tournament_invitation, "retry", fake_retry)

    with pytest.raises(RetryRaised):
        notifications.send_tournament_invitation.run(123)

    assert captured == {"exc": error, "countdown": 2}


@pytest.mark.unit
def test_invitation_task_does_not_retry_permanent_smtp_failure(monkeypatch):
    error = smtplib.SMTPDataError(550, b"message rejected")
    retry_called = False

    def fail_delivery(participant_id: int) -> bool:
        raise error

    def fake_retry(**kwargs):
        nonlocal retry_called
        retry_called = True

    monkeypatch.setattr(notifications, "deliver_tournament_invitation", fail_delivery)
    monkeypatch.setattr(notifications.send_tournament_invitation, "retry", fake_retry)

    with pytest.raises(smtplib.SMTPDataError) as exc_info:
        notifications.send_tournament_invitation.run(123)

    assert exc_info.value is error
    assert retry_called is False


@pytest.mark.unit
def test_retry_backoff_is_bounded_for_three_retries():
    assert [notifications._retry_countdown(retry) for retry in range(3)] == [2, 4, 8]
