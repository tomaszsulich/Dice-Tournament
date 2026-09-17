from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from accounts.services.session_activity import record_activity

ACTIVE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

PASSIVE_PATHS = {
    "/api/auth/jwt/refresh/",
    "/api/auth/logout/",
    "/api/auth/users/reset-password/",
    "/api/auth/users/reset-password-confirm/",
}


class SessionActivityMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        family_id = getattr(request, "_dice_session_family_id", None)

        if (
            family_id
            and request.method in ACTIVE_METHODS
            and request.path not in PASSIVE_PATHS
            and response.status_code < 400
        ):
            record_activity(family_id=family_id)

        return response
