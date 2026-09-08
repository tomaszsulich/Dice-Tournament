from django.http import HttpResponse

from accounts.middleware import SessionActivityMiddleware


def test_successful_authenticated_unsafe_action_records_activity(rf, monkeypatch):
    recorded_family_ids = []

    monkeypatch.setattr(
        "accounts.middleware.record_activity",
        lambda *, family_id: recorded_family_ids.append(family_id),
    )

    request = rf.post("/api/example-action/")
    request._dice_session_family_id = "test-family-id"

    middleware = SessionActivityMiddleware(lambda _request: HttpResponse(status=204))
    middleware(request)

    assert recorded_family_ids == ["test-family-id"]


def test_passive_authenticated_action_does_not_record_activity(rf, monkeypatch):
    recorded_family_ids = []

    monkeypatch.setattr(
        "accounts.middleware.record_activity",
        lambda *, family_id: recorded_family_ids.append(family_id),
    )

    request = rf.post("/api/auth/jwt/refresh/")
    request._dice_session_family_id = "test-family-id"

    middleware = SessionActivityMiddleware(lambda _request: HttpResponse(status=200))
    middleware(request)

    assert recorded_family_ids == []
