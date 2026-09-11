from http.cookies import CookieError, SimpleCookie

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from accounts.services.session_activity import SessionRejected, validate_session_family
from tournaments.models import Game, Tournament
from tournaments.realtime.publisher import organizer_group_name, table_group_name


@database_sync_to_async
def _user_from_access_cookie(raw_token: str | None):
    if not raw_token:
        return AnonymousUser()

    try:
        token = AccessToken(raw_token)
        family_id = token.get("session_family")

        if not family_id:
            return AnonymousUser()

        validate_session_family(family_id=family_id)
        return User.objects.get(pk=token["user_id"], is_active=True)

    except (TokenError, SessionRejected, User.DoesNotExist, ValueError, TypeError):
        return AnonymousUser()


class JwtCookieAuthMiddleware:
    """Authenticate WebSockets only through the hardened access-token cookie."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        cookie_header = dict(scope.get("headers", [])).get(b"cookie", b"")
        raw_token = _cookie_value(cookie_header, settings.JWT_ACCESS_COOKIE)
        scope["user"] = await _user_from_access_cookie(raw_token)
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


class TableConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        game_id = self.scope["url_route"]["kwargs"]["game_id"]

        if not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        if not await self._may_view_table(user.pk, game_id):
            await self.close(code=4403)
            return

        self.group_name = table_group_name(game_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, _code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def table_changed(self, event):
        await self.send_json(
            {
                "type": "table_changed",
                "table_id": event["table_id"],
                "state_version": event["state_version"],
            }
        )

    @database_sync_to_async
    def _may_view_table(self, user_id: int, game_id: int) -> bool:
        try:
            game = Game.objects.select_related("round__tournament").get(pk=game_id)
        except Game.DoesNotExist:
            return False

        is_participant = game.game_participants.filter(
            tournament_participant__player_profile__user_id=user_id
        ).exists()

        is_organizer = game.round.tournament.organizers.filter(pk=user_id).exists()
        return is_participant or is_organizer


class OrganizerConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        tournament_id = self.scope["url_route"]["kwargs"]["tournament_id"]

        if not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        if not await self._is_organizer(user.pk, tournament_id):
            await self.close(code=4403)
            return

        self.group_name = organizer_group_name(tournament_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, _code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def table_changed(self, event):
        await self.send_json(
            {
                "type": "table_changed",
                "table_id": event["table_id"],
                "state_version": event["state_version"],
            }
        )

    @database_sync_to_async
    def _is_organizer(self, user_id: int, tournament_id: int) -> bool:
        return Tournament.objects.filter(
            pk=tournament_id,
            organizers__pk=user_id,
        ).exists()
