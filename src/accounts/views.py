from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def login_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/login.html")


def register_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/register.html")


def profile_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/profile.html")


def profile_setup_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/profile_setup.html")


def profile_edit_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/profile_edit.html")


def password_reset_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/password_reset.html")


def set_password_page(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/set_password.html")
