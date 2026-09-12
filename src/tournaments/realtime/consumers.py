import asyncio
from http.cookies import CookieError, SimpleCookie

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from accounts.services.session_activity import (
    SessionRejected,
    validate_session_family,
)
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import ParticipantStatus
from tournaments.models import Game, Tournament, TournamentParticipant
from tournaments.realtime.publisher import (
    organizer_group_name,
    participant_group_name,
    table_group_name,
)
from tournaments.services.connection_state import (
    RECONNECT_GRACE,
    mark_connected,
    mark_reconnecting,
    official_game_for_participant,
    refresh_connection_status,
)

SESSION_RECHECK_SECONDS = 30


@database_sync_to_async
def _identity_from_access_cookie(raw_token: str | None):
    if not raw_token:
        return AnonymousUser(), None

    try:
        token = AccessToken(raw_token)
        family_id = token.get("session_family")

        if not family_id:
            return AnonymousUser(), None

        family = validate_session_family(family_id=family_id)
        user = User.objects.get(pk=token["user_id"], is_active=True)
        return user, family.pk

    except (TokenError, SessionRejected, User.DoesNotExist, ValueError, TypeError):
        return AnonymousUser(), None


@database_sync_to_async
def _session_family_is_valid(family_id) -> bool:
    if family_id is None:
        return False

    try:
        validate_session_family(family_id=family_id)
    except (SessionRejected, ValueError, TypeError):
        return False

    return True


class JwtCookieAuthMiddleware:
    """Authenticate WebSockets only through the hardened access-token cookie."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        cookie_header = dict(scope.get("headers", [])).get(b"cookie", b"")
        raw_token = _cookie_value(cookie_header, settings.JWT_ACCESS_COOKIE)
        user, family_id = await _identity_from_access_cookie(raw_token)

        scope["user"] = user
        scope["session_family_id"] = family_id
        return await self.app(scope, receive, send)


def _cookie_value(raw_header: bytes, key: str) -> str | None:
    if not raw_header:
        return None

    cookie = SimpleCookie()

    try:
        cookie.load(raw_header.decode("latin-1"))
    except CookieError:
        return None

    morsel = cookie.get(key)
    return morsel.value if morsel is not None else None


class SessionAwareWebsocketConsumer(AsyncJsonWebsocketConsumer):
    async def _accept_authenticated(self):
        await self.accept()
        self._session_watchdog_task = asyncio.create_task(self._watch_session_family())

    async def _reject(self, code: int):
        await self.accept()
        await self.close(code=code)

    async def _watch_session_family(self):
        while True:
            await asyncio.sleep(SESSION_RECHECK_SECONDS)

            if not await _session_family_is_valid(self.scope.get("session_family_id")):
                await self.close(code=4401)
                return

    def _stop_session_watchdog(self):
        task = getattr(self, "_session_watchdog_task", None)

        if task is not None and task is not asyncio.current_task():
            task.cancel()


class TableConsumer(SessionAwareWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        game_id = self.scope["url_route"]["kwargs"]["game_id"]

        if not getattr(user, "is_authenticated", False):
            await self._reject(4401)
            return

        allowed, participant_id, tournament_id = await self._table_access(
            user.pk, game_id
        )

        if not allowed:
            await self._reject(4403)
            return

        self.game_id = game_id
        self.participant_id = participant_id
        self.tournament_id = tournament_id
        self.group_name = table_group_name(game_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        if self.participant_id is not None:
            self.assignment_group_name = participant_group_name(self.participant_id)

            await self.channel_layer.group_add(
                self.assignment_group_name,
                self.channel_name,
            )

            if not await database_sync_to_async(mark_connected)(
                participant_id=self.participant_id,
                channel_name=self.channel_name,
            ):
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name,
                )

                await self.channel_layer.group_discard(
                    self.assignment_group_name,
                    self.channel_name,
                )

                await self._reject(4403)
                return

            await self.channel_layer.group_send(
                organizer_group_name(self.tournament_id),
                {
                    "type": "participant.connection_changed",
                    "participant_id": self.participant_id,
                    "connection_status": "connected",
                },
            )

        await self._accept_authenticated()

    async def disconnect(self, _code):
        self._stop_session_watchdog()
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if hasattr(self, "assignment_group_name"):
            await self.channel_layer.group_discard(
                self.assignment_group_name,
                self.channel_name,
            )

        if getattr(self, "participant_id", None) is not None:
            started = await database_sync_to_async(mark_reconnecting)(
                participant_id=self.participant_id,
                channel_name=self.channel_name,
            )

            if started:
                asyncio.create_task(self._mark_disconnected_after_grace())

    async def _mark_disconnected_after_grace(self):
        await asyncio.sleep(RECONNECT_GRACE.total_seconds())

        status = await database_sync_to_async(refresh_connection_status)(
            participant_id=self.participant_id
        )

        if status == "disconnected":
            await self.channel_layer.group_send(
                organizer_group_name(self.tournament_id),
                {
                    "type": "participant.connection_changed",
                    "participant_id": self.participant_id,
                    "connection_status": status,
                },
            )

    async def table_changed(self, event):
        if not await self._may_still_view_table():
            await self.close(code=4403)
            return

        await self.send_json(
            {
                "type": "table_changed",
                "table_id": event["table_id"],
                "state_version": event["state_version"],
            }
        )

    async def table_assignment_changed(self, event):
        if self.participant_id is None:
            return

        await self.send_json(
            {
                "type": "table_assignment_changed",
                "table_id": event["table_id"],
                "state_version": event["state_version"],
                "target_url": event["target_url"],
            }
        )

    @database_sync_to_async
    def _table_access(
        self, user_id: int, game_id: int
    ) -> tuple[bool, int | None, int | None]:
        try:
            game = Game.objects.select_related("round__tournament").get(pk=game_id)
        except Game.DoesNotExist:
            return False, None, None

        participant = (
            TournamentParticipant.objects.filter(
                tournament=game.round.tournament,
                player_profile__user_id=user_id,
            )
            .select_related("player_profile")
            .first()
        )

        if participant is None or participant.status != ParticipantStatus.ACTIVE:
            return False, None, game.round.tournament_id

        official_game = official_game_for_participant(participant)

        if official_game is None or official_game.pk != game_id:
            return False, None, game.round.tournament_id

        return True, participant.pk, game.round.tournament_id

    @database_sync_to_async
    def _may_still_view_table(self) -> bool:
        user = self.scope.get("user", AnonymousUser())

        if not getattr(user, "is_authenticated", False):
            return False

        if self.participant_id is None:
            return False

        participant = TournamentParticipant.objects.filter(
            pk=self.participant_id,
            player_profile__user_id=user.pk,
            status=ParticipantStatus.ACTIVE,
        ).first()

        if participant is None:
            return False

        official_game = official_game_for_participant(participant)
        return official_game is not None and official_game.pk == self.game_id


class ParticipantAssignmentConsumer(SessionAwareWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", AnonymousUser())

        if not getattr(user, "is_authenticated", False):
            await self._reject(4401)
            return

        participant_ids, assignments = await self._assignment_context(user.pk)

        if not participant_ids:
            await self._reject(4403)
            return

        self.assignment_group_names = [
            participant_group_name(participant_id) for participant_id in participant_ids
        ]

        for group_name in self.assignment_group_names:
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self._accept_authenticated()

        if len(assignments) == 1:
            game_id, state_version = assignments[0]
            await self.send_json(
                {
                    "type": "table_assignment_changed",
                    "table_id": game_id,
                    "state_version": state_version,
                    "target_url": reverse("participant-table", args=(game_id,)),
                }
            )

    async def disconnect(self, _code):
        self._stop_session_watchdog()

        for group_name in getattr(self, "assignment_group_names", []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def table_assignment_changed(self, event):
        await self.send_json(
            {
                "type": "table_assignment_changed",
                "table_id": event["table_id"],
                "state_version": event["state_version"],
                "target_url": event["target_url"],
            }
        )

    @database_sync_to_async
    def _assignment_context(
        self, user_id: int
    ) -> tuple[list[int], list[tuple[int, int]]]:
        participants = list(
            TournamentParticipant.objects.filter(
                player_profile__user_id=user_id,
                status__in=(
                    ParticipantStatus.REGISTERED,
                    ParticipantStatus.ACTIVE,
                ),
            )
            .select_related("player_profile")
            .order_by("pk")
        )

        participant_ids = [participant.pk for participant in participants]
        assignments: list[tuple[int, int]] = []

        for participant in participants:
            game = official_game_for_participant(participant)

            if game is None or game.round.status != RoundStatus.ACTIVE:
                continue

            assignments.append((game.pk, game.state_version))

        return participant_ids, assignments


class OrganizerConsumer(SessionAwareWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        tournament_id = self.scope["url_route"]["kwargs"]["tournament_id"]

        if not getattr(user, "is_authenticated", False):
            await self._reject(4401)
            return

        if not await self._is_organizer(user.pk, tournament_id):
            await self._reject(4403)
            return

        self.tournament_id = tournament_id
        self.group_name = organizer_group_name(tournament_id)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self._accept_authenticated()

    async def disconnect(self, _code):
        self._stop_session_watchdog()
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def table_changed(self, event):
        if not await self._is_current_organizer():
            await self.close(code=4403)
            return

        await self.send_json(
            {
                "type": "table_changed",
                "table_id": event["table_id"],
                "state_version": event["state_version"],
            }
        )

    async def participant_connection_changed(self, event):
        if not await self._is_current_organizer():
            await self.close(code=4403)
            return

        await self.send_json(
            {
                "type": "participant_connection_changed",
                "participant_id": event["participant_id"],
                "connection_status": event["connection_status"],
            }
        )

    @database_sync_to_async
    def _is_organizer(self, user_id: int, tournament_id: int) -> bool:
        return Tournament.objects.filter(
            pk=tournament_id,
            organizers__pk=user_id,
        ).exists()

    async def _is_current_organizer(self) -> bool:
        user = self.scope.get("user", AnonymousUser())

        if not getattr(user, "is_authenticated", False):
            return False

        return await self._is_organizer(user.pk, self.tournament_id)
