import logging
import uuid
from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.errors import domain_error

logger = logging.getLogger(__name__)


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Preserve DRF errors and safely identify unexpected server failures."""
    response = drf_exception_handler(exc, context)

    if response is not None:
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
