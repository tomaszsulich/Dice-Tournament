from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from accounts.authentication import CookieOrHeaderJWTAuthentication
from tournaments.services.connection_state import active_game_for_user


def _active_game_redirect(request: HttpRequest) -> HttpResponse | None:
    drf_request = Request(request)

    try:
        authenticated = CookieOrHeaderJWTAuthentication().authenticate(drf_request)
    except AuthenticationFailed:
        return None

    if authenticated is None:
        return None

    user, _token = authenticated
    game = active_game_for_user(user.pk)

    if game is None:
        return None

    return redirect("participant-table", game_id=game.pk)


def login_page(request: HttpRequest) -> HttpResponse:
    return _active_game_redirect(request) or render(request, "accounts/login.html")


def register_page(request: HttpRequest) -> HttpResponse:
    return _active_game_redirect(request) or render(request, "accounts/register.html")


def profile_page(request: HttpRequest) -> HttpResponse:
    return _active_game_redirect(request) or render(request, "accounts/profile.html")


def profile_setup_page(request: HttpRequest) -> HttpResponse:
    return _active_game_redirect(request) or render(
        request, "accounts/profile_setup.html"
    )


def profile_edit_page(request: HttpRequest) -> HttpResponse:
    return _active_game_redirect(request) or render(
        request, "accounts/profile_edit.html"
    )


def password_reset_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/password_reset.html")


def set_password_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/set_password.html")
