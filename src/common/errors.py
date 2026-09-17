from rest_framework.response import Response

SAFE_ERROR_MESSAGES = {
    "NOT_YOUR_TURN": "Not your turn.",
    "CATEGORY_ALREADY_USED": "Category already used.",
    "SESSION_EXPIRED": "Session expired. Sign in again.",
    "IDEMPOTENCY_CONFLICT": ("Request key already used for another action."),
    "TOURNAMENT_FULL": "Tournament is full.",
    "PLAYER_PROFILE_EXISTS": "Player profile already exists.",
    "PLAYER_PROFILE_UNCHANGED": "Player profile is already up to date.",
    "ACTIVE_GAME_IN_PROGRESS": (
        "Finish your active game before changing account details."
    ),
}


def domain_error(code: str, response_status: int, *, details=None):
    """Return a stable machine code without exposing exception text."""
    payload = {
        "code": code,
        "message": SAFE_ERROR_MESSAGES.get(code, "Request failed."),
    }

    if details is not None:
        payload["details"] = details

    return Response(payload, status=response_status)
