import logging
import uuid
from typing import Any

from django.template.response import TemplateResponse
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.errors import domain_error

logger = logging.getLogger(__name__)

_BROWSER_ERROR_PATH_PREFIXES = ("/tables/", "/api/docs/", "/api/schema/")
_BROWSER_ERROR_CONTENT = {
    401: (
        "Sign in required",
        "Sign in to open this page.",
    ),
    403: (
        "Access denied",
        "You cannot open this page.",
    ),
    404: (
        "Not found",
        "Page unavailable or not visible to this account.",
    ),
}


def _browser_error_response(request, status_code: int) -> TemplateResponse | None:
    accept = request._request.headers.get("Accept", "")

    if "text/html" not in accept:
        return None

    if not request.path.startswith(_BROWSER_ERROR_PATH_PREFIXES):
        return None

    title, message = _BROWSER_ERROR_CONTENT.get(
        status_code,
        ("Request failed", "Try again."),
    )

    return TemplateResponse(
        request._request,
        "api/http_error.html",
        {
            "status_code": status_code,
            "title": title,
            "message": message,
            "request_path": request.path,
            "show_login": status_code == 401,
        },
        status=status_code,
    )


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Preserve API errors and render safe HTML for browser-facing endpoints."""
    response = drf_exception_handler(exc, context)

    if response is not None:
        request = context.get("request")

        if request is not None:
            browser_response = _browser_error_response(request, response.status_code)

            if browser_response is not None:
                return browser_response

        return response

    correlation_id = str(uuid.uuid4())

    logger.error(
        "Unhandled API error correlation_id=%s",
        correlation_id,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return domain_error(
        "INTERNAL_ERROR",
        500,
        details={"correlation_id": correlation_id},
    )
