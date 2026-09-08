from django.conf import settings
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.api.schema import LogoutRequestSerializer
from accounts.authentication import enforce_csrf
from accounts.jwt import SessionTokenObtainPairSerializer, SessionTokenRefreshSerializer
from accounts.models import PlayerProfile, SessionFamily
from accounts.serializers import PlayerProfileSerializer
from accounts.services.session_activity import revoke_session_family
from api.schema import AUTHENTICATED_ERROR_RESPONSES, VALIDATION_ERROR_RESPONSE


def _set_auth_cookies(response: Response) -> None:
    access = response.data.get("access") if isinstance(response.data, dict) else None
    refresh = response.data.get("refresh") if isinstance(response.data, dict) else None

    common = {
        "httponly": True,
        "secure": settings.JWT_COOKIE_SECURE,
        "samesite": settings.JWT_COOKIE_SAMESITE,
        "path": "/",
    }

    if access:
        response.set_cookie(
            settings.JWT_ACCESS_COOKIE,
            access,
            max_age=15 * 60,
            **common,
        )

    if refresh:
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE,
            refresh,
            max_age=8 * 60 * 60,
            **common,
        )


class SessionTokenObtainPairView(TokenObtainPairView):
    serializer_class = SessionTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            get_token(request._request)
            _set_auth_cookies(response)

        return response


class SessionTokenRefreshView(TokenRefreshView):
    serializer_class = SessionTokenRefreshSerializer
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs):
        data = request.data.copy()

        if not data.get("refresh"):
            refresh_cookie = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)

            if refresh_cookie:
                enforce_csrf(request)
                data["refresh"] = refresh_cookie

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)

        _set_auth_cookies(response)
        return response


@extend_schema(
    responses={
        **AUTHENTICATED_ERROR_RESPONSES,
        200: PlayerProfileSerializer,
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request: Request):
    profile = get_object_or_404(PlayerProfile, user=request.user)
    serializer = PlayerProfileSerializer(profile)
    return Response(serializer.data)


@extend_schema(
    request=LogoutRequestSerializer,
    responses={
        **AUTHENTICATED_ERROR_RESPONSES,
        204: None,
        400: VALIDATION_ERROR_RESPONSE,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request: Request):
    refresh_token = request.data.get("refresh") or request.COOKIES.get(
        settings.JWT_REFRESH_COOKIE
    )

    if not refresh_token:
        return Response(
            {"refresh": ["This field is required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = RefreshToken(refresh_token)

        if str(token["user_id"]) != str(request.user.pk):
            return Response(
                {"refresh": ["Token does not belong to the authenticated user."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        family = SessionFamily.objects.get(
            pk=token["session_family"], user=request.user
        )

        token.blacklist()
        revoke_session_family(family=family)

    except (TokenError, SessionFamily.DoesNotExist, KeyError, ValueError, TypeError):
        return Response(
            {"refresh": ["Invalid or expired token."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = Response(status=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.JWT_ACCESS_COOKIE, path="/")
    response.delete_cookie(settings.JWT_REFRESH_COOKIE, path="/")
    return response
