import smtplib
from typing import Protocol

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage

from tournaments.domain.tournament.types import ParticipantStatus, TournamentStatus
from tournaments.models import TournamentParticipant


class InvitationMailer(Protocol):
    def send(self, *, recipient: str, tournament_name: str) -> None: ...


class DjangoInvitationMailer:
    def send(self, *, recipient: str, tournament_name: str) -> None:
        message = EmailMessage(
            subject=f"Tournament invitation: {tournament_name}",
            body=(
                f'You have been added to the tournament "{tournament_name}".\n\n'
                "Sign in to Dice Tournament to view your participation."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )

        message.send(using="default")


def _is_retryable_mail_error(exc: BaseException) -> bool:
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return any(400 <= code < 500 for code, _message in exc.recipients.values())

    if isinstance(exc, smtplib.SMTPResponseException):
        return 400 <= exc.smtp_code < 500

    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return True

    if isinstance(exc, smtplib.SMTPException):
        return False

    return isinstance(exc, OSError)


def _retry_countdown(retries: int) -> int:
    return 2 ** (retries + 1)


def deliver_tournament_invitation(
    participant_id: int,
    *,
    mailer: InvitationMailer | None = None,
) -> bool:
    """Reload current state and send only while the invitation is still applicable."""
    participant = (
        TournamentParticipant.objects.select_related(
            "tournament",
            "player_profile__user",
        )
        .filter(pk=participant_id)
        .first()
    )

    if (
        participant is None
        or participant.status != ParticipantStatus.REGISTERED
        or participant.tournament.status
        not in {TournamentStatus.DRAFT, TournamentStatus.REGISTRATION}
    ):
        return False

    recipient = participant.player_profile.user.email.strip()

    if not recipient:
        return False

    (mailer or DjangoInvitationMailer()).send(
        recipient=recipient,
        tournament_name=participant.tournament.name,
    )

    return True


@shared_task(bind=True, max_retries=3)
def send_tournament_invitation(self, participant_id: int) -> bool:
    """Send an organizer invitation with bounded retry for transient mail errors."""
    try:
        return deliver_tournament_invitation(participant_id)
    except (smtplib.SMTPException, OSError) as exc:
        if not _is_retryable_mail_error(exc):
            raise

        countdown = _retry_countdown(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc
