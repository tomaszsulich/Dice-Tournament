from typing import Any

from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token

from accounts.services.session_activity import SessionRejected, validate_session_family

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def enforce_csrf(request: Request) -> None:
    check = CSRFCheck(lambda _request: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})

    if reason:
        raise PermissionDenied(f"CSRF Failed: {reason}")


class CookieOrHeaderJWTAuthentication(JWTAuthentication):
    def authenticate(self, request: Request) -> tuple[Any, Token] | None:
        header = self.get_header(request)
        cookie_auth = header is None

        if cookie_auth:
            raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE)

            if raw_token is None:
                return None

            if request.method not in SAFE_METHODS:
                enforce_csrf(request)
        else:
            raw_token = self.get_raw_token(header)

            if raw_token is None:
                return None

        validated_token = self.get_validated_token(raw_token)
        family_id = validated_token.get("session_family")

        if family_id is None:
            raise AuthenticationFailed(
                {"code": "SESSION_INVALID", "detail": "Session is not valid."}
            )

        try:
            validate_session_family(family_id=family_id)
        except SessionRejected as exc:
            raise AuthenticationFailed(
                {"code": exc.code, "detail": "Reauthentication is required."}
            ) from exc

        user = self.get_user(validated_token)
        request._request._dice_session_family_id = str(family_id)
        return user, validated_token
