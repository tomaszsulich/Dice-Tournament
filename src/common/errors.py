from rest_framework.response import Response

SAFE_ERROR_MESSAGES = {
    "NOT_YOUR_TURN": "This action is not available outside your turn.",
    "CATEGORY_ALREADY_USED": "This category has already been used.",
    "SESSION_EXPIRED": "The session has expired. Sign in again.",
    "IDEMPOTENCY_CONFLICT": (
        "The idempotency key was already used for another request."
    ),
    "TOURNAMENT_FULL": "The tournament has no available places.",
}


def domain_error(code: str, response_status: int, *, details=None):
    """Return a stable machine code without exposing exception text."""
    payload = {
        "code": code,
        "message": SAFE_ERROR_MESSAGES.get(code, "The request could not be completed."),
    }

    if details is not None:
        payload["details"] = details

    return Response(payload, status=response_status)
