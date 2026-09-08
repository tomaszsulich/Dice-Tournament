from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from django.conf import settings
from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import UntypedToken

if TYPE_CHECKING:
    from rest_framework.views import APIView


class AuthSecurityThrottle(SimpleRateThrottle):
    """Rate-limit sensitive auth operations by IP and account identity."""

    scope = "auth_security"

    _paths = {
        "/api/auth/jwt/create/",
        "/api/auth/jwt/refresh/",
        "/api/auth/users/reset-password/",
    }

    def get_cache_key(self, request: Request, _view: APIView) -> str | None:
        if request.path not in self._paths:
            return None

        ip = self.get_ident(request)
        account = self._account_identifier(request)
        digest = hashlib.sha256(f"{ip}:{account}".encode()).hexdigest()

        return self.cache_format % {"scope": self.scope, "ident": digest}

    @staticmethod
    def _account_identifier(request: Request) -> str:
        for field in ("username", "email"):
            value = request.data.get(field)

            if value:
                return str(value).strip().casefold()

        raw_refresh = request.data.get("refresh") or request.COOKIES.get(
            settings.JWT_REFRESH_COOKIE
        )

        if raw_refresh:
            try:
                token = UntypedToken(raw_refresh)
                return f"user:{token.get('user_id', 'unknown')}"
            except TokenError:
                pass

        return "anonymous"


class GameCommandThrottle(SimpleRateThrottle):
    """Rate-limit game commands per authenticated user and game."""

    scope = "game_command"

    _pattern = re.compile(
        r"^/api/games/(?P<game_id>\d+)/(roll|holds|choose-category)/$"
    )

    def get_cache_key(self, request: Request, _view: APIView) -> str | None:
        match = self._pattern.match(request.path)

        if not match or not request.user or not request.user.is_authenticated:
            return None

        ident = f"{request.user.pk}:{match.group('game_id')}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class RegistrationCommandThrottle(SimpleRateThrottle):
    """Rate-limit registration commands per user and tournament."""

    scope = "registration_command"

    _pattern = re.compile(r"^/api/tournaments/(?P<tournament_id>\d+)/(join|leave)/$")

    def get_cache_key(self, request: Request, _view: APIView) -> str | None:
        match = self._pattern.match(request.path)

        if not match or not request.user or not request.user.is_authenticated:
            return None

        ident = f"{request.user.pk}:{match.group('tournament_id')}"
        return self.cache_format % {"scope": self.scope, "ident": ident}
