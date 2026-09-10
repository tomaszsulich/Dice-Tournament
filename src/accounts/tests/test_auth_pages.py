from html import unescape

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_login_page_is_public(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200
    assert b"Welcome back" in response.content
    assert "Create an\u00a0account" in unescape(response.content.decode())


@pytest.mark.django_db
def test_registration_page_explains_optional_player_profile(client):
    response = client.get(reverse("register"))
    assert response.status_code == 200
    assert b"Create your account" in response.content

    rendered = unescape(response.content.decode())
    assert "Create a\u00a0player profile" in rendered
    assert "Needed to\u00a0join and play in\u00a0tournaments." in rendered


@pytest.mark.django_db
def test_profile_setup_page_is_public_shell(client):
    response = client.get(reverse("profile-setup"))
    assert response.status_code == 200

    rendered = unescape(response.content.decode())
    assert "Create player\u00a0profile" in rendered


@pytest.mark.django_db
def test_password_reset_page_keeps_reset_credentials_out_of_visible_form(client):
    response = client.get(reverse("password-reset"))

    assert response.status_code == 200
    assert b"Reset your password" in response.content
    assert b'name="uid"' not in response.content
    assert b'name="token"' not in response.content


@pytest.mark.django_db
def test_set_password_page_does_not_render_uid_or_token_fields(client):
    response = client.get(
        reverse("set-password"),
        {"uid": "example-uid", "token": "example-token"},
    )

    assert response.status_code == 200
    assert b"Choose a new password" in response.content
    assert b'name="uid"' not in response.content
    assert b'name="token"' not in response.content
    assert b"example-uid" not in response.content
    assert b"example-token" not in response.content


@pytest.mark.django_db
def test_api_docs_accept_authenticated_staff_django_session(client):
    staff = UserFactory.create(is_staff=True)
    client.force_login(staff)

    response = client.get(reverse("swagger-ui"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_browser_facing_unauthorized_page_is_human_readable(client):
    response = client.get(
        reverse("participant-table", args=[999]),
        HTTP_ACCEPT="text/html",
    )

    assert response.status_code == 401
    assert b"Sign in required" in response.content
    assert b"Authentication credentials were not provided" not in response.content


@pytest.mark.django_db
def test_profile_overview_does_not_require_player_profile_at_template_boundary(client):
    response = client.get(reverse("profile"))

    assert response.status_code == 200
    assert b"Your account" in response.content
    assert b"Create player" in response.content
    assert b"Log" in response.content


@pytest.mark.unit
def test_login_redirects_to_account_overview_instead_of_forcing_profile_setup():
    from pathlib import Path

    script = Path("src/accounts/static/accounts/js/login.js").read_text(
        encoding="utf-8"
    )

    assert 'DiceAuth.safeNext() || "/profile/"' in script
    assert 'DiceAuth.safeNext() || "/profile/setup/"' not in script


@pytest.mark.django_db
def test_profile_edit_page_is_browser_shell(client):
    response = client.get(reverse("profile-edit"))
    rendered = unescape(response.content.decode("utf-8"))

    assert response.status_code == 200
    assert "Edit player profile" in rendered
    assert b"profile_edit.js" in response.content
    assert b"Save changes" in response.content


@pytest.mark.unit
def test_profile_edit_ui_rejects_same_values_before_patch():
    from pathlib import Path

    script = Path("src/accounts/static/accounts/js/profile_edit.js").read_text(
        encoding="utf-8"
    )

    assert 'method: "PATCH"' in script
    assert "next.display_name === original.display_name" in script
    assert "next.nickname === original.nickname" in script
    assert 'payload.code === "PLAYER_PROFILE_UNCHANGED"' in script
