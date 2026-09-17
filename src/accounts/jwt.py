from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from accounts.models import SessionFamily, User
from accounts.services.session_activity import (
    SessionRejected,
    create_session_family,
    revoke_session_family,
    validate_session_family,
)

SESSION_FAMILY_CLAIM = "session_family"


class SessionTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: User) -> RefreshToken:
        family = create_session_family(user=user)

        token = super().get_token(user)
        token[SESSION_FAMILY_CLAIM] = str(family.pk)
        token["exp"] = int(family.absolute_expires_at.timestamp())

        return token


class SessionTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        raw_refresh = attrs["refresh"]

        try:
            untyped = UntypedToken(raw_refresh)
            family_id = untyped.get(SESSION_FAMILY_CLAIM)
        except TokenError as exc:
            raise serializers.ValidationError(
                {"code": "SESSION_INVALID", "detail": "Reauthentication is required."}
            ) from exc

        try:
            with transaction.atomic():
                family = SessionFamily.objects.select_for_update().get(pk=family_id)
                validate_session_family(family_id=family.pk)

                reuse_error = None

                try:
                    data = super().validate(attrs)
                except TokenError as exc:
                    revoke_session_family(family=family)
                    reuse_error = exc

        except (
            SessionFamily.DoesNotExist,
            ValueError,
            TypeError,
            SessionRejected,
        ) as exc:
            code = exc.code if isinstance(exc, SessionRejected) else "SESSION_INVALID"

            raise serializers.ValidationError(
                {"code": code, "detail": "Reauthentication is required."}
            ) from exc

        if reuse_error is not None:
            raise serializers.ValidationError(
                {
                    "code": "SESSION_REUSE_DETECTED",
                    "detail": "Reauthentication is required.",
                }
            ) from reuse_error

        rotated = RefreshToken(data["refresh"])
        rotated[SESSION_FAMILY_CLAIM] = str(family.pk)
        rotated["exp"] = int(family.absolute_expires_at.timestamp())

        data["refresh"] = str(rotated)
        return data
