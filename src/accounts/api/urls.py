import djoser.urls
import djoser.urls.jwt
from django.urls import include, path

from .djoser_views import DiceUserViewSet
from .views import (
    SessionTokenObtainPairView,
    SessionTokenRefreshView,
    logout,
    profile,
)

_OVERRIDDEN_DJOSER_URL_NAMES = {
    "user-list",
    "user-set-password",
    "user-reset-password",
    "user-reset-password-confirm",
}

_DJOSER_URLPATTERNS = [
    pattern
    for pattern in djoser.urls.urlpatterns
    if getattr(pattern, "name", None) not in _OVERRIDDEN_DJOSER_URL_NAMES
]


urlpatterns = [
    path(
        "auth/users/",
        DiceUserViewSet.as_view({"post": "create"}),
        name="user-list",
    ),
    path("auth/jwt/create/", SessionTokenObtainPairView.as_view(), name="jwt-create"),
    path("auth/jwt/refresh/", SessionTokenRefreshView.as_view(), name="jwt-refresh"),
    path("auth/logout/", logout),
    path(
        "auth/users/set-password/",
        DiceUserViewSet.as_view({"post": "set_password"}),
        name="user-set-password",
    ),
    path(
        "auth/users/reset-password/",
        DiceUserViewSet.as_view({"post": "reset_password"}),
        name="user-reset-password",
    ),
    path(
        "auth/users/reset-password-confirm/",
        DiceUserViewSet.as_view({"post": "reset_password_confirm"}),
        name="user-reset-password-confirm",
    ),
    path("auth/", include(_DJOSER_URLPATTERNS)),
    path("auth/", include(djoser.urls.jwt)),
    path("profile/", profile),
]
