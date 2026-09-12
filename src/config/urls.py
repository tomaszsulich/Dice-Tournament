"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser

from accounts.authentication import CookieOrHeaderJWTAuthentication
from accounts.views import (
    login_page,
    password_reset_page,
    profile_edit_page,
    profile_page,
    profile_setup_page,
    register_page,
    set_password_page,
)
from tournaments.organizer_dashboard_views import (
    organizer_dashboard_page,
    participant_comparison_page,
)
from tournaments.views import participant_table


def health_live(_request: HttpRequest):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", login_page, name="login"),
    path("register/", register_page, name="register"),
    path("profile/", profile_page, name="profile"),
    path("profile/setup/", profile_setup_page, name="profile-setup"),
    path("profile/edit/", profile_edit_page, name="profile-edit"),
    path("forgot-password/", password_reset_page, name="password-reset"),
    path("set-password/", set_password_page, name="set-password"),
    path("api/", include("accounts.api.urls")),
    path("api/", include("tournaments.api.urls")),
    path("tables/<int:game_id>/", participant_table, name="participant-table"),
    path(
        "tournaments/<int:tournament_id>/organizer/",
        organizer_dashboard_page,
        name="organizer-dashboard",
    ),
    path(
        "comparisons/participants/<int:participant_id>/",
        participant_comparison_page,
        name="participant-comparison",
    ),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(
            authentication_classes=[
                SessionAuthentication,
                CookieOrHeaderJWTAuthentication,
            ],
            permission_classes=[IsAdminUser],
        ),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[
                SessionAuthentication,
                CookieOrHeaderJWTAuthentication,
            ],
            permission_classes=[IsAdminUser],
        ),
        name="swagger-ui",
    ),
    path("health/live/", health_live),
]
