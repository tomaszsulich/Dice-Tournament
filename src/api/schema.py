from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse
from rest_framework import serializers

DOMAIN_ERROR_EXAMPLE = OpenApiExample(
    "Domain error",
    value={
        "code": "NOT_YOUR_TURN",
        "message": "This action is not available outside your turn.",
    },
    response_only=True,
)


class DomainErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)


class InternalErrorDetailsSerializer(serializers.Serializer):
    correlation_id = serializers.CharField()


class InternalErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = InternalErrorDetailsSerializer()


DOMAIN_ERROR_RESPONSE = OpenApiResponse(
    response=DomainErrorSerializer,
    description="Domain error response with a stable machine-readable code.",
    examples=[DOMAIN_ERROR_EXAMPLE],
)

VALIDATION_ERROR_RESPONSE = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Standard DRF validation error representation.",
)

VALIDATION_OR_DOMAIN_ERROR_RESPONSE = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description=(
        "Either a standard DRF validation error or a domain error response "
        "with a stable machine-readable code."
    ),
    examples=[DOMAIN_ERROR_EXAMPLE],
)

AUTHENTICATION_ERROR_RESPONSE = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Authentication or session error response.",
)

THROTTLED_RESPONSE = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Request throttled by DRF.",
)

INTERNAL_ERROR_RESPONSE = OpenApiResponse(
    response=InternalErrorSerializer,
    description=(
        "Safe unexpected server error. The correlation ID can be matched "
        "with server logs."
    ),
    examples=[
        OpenApiExample(
            "Internal error",
            value={
                "code": "INTERNAL_ERROR",
                "message": "The request could not be completed.",
                "details": {"correlation_id": "1f07be26-0efb-4568-b6d7-1cbb0df978ac"},
            },
            response_only=True,
        )
    ],
)

AUTHENTICATED_ERROR_RESPONSES = {
    401: AUTHENTICATION_ERROR_RESPONSE,
    429: THROTTLED_RESPONSE,
    500: INTERNAL_ERROR_RESPONSE,
}


class CookieOrHeaderJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CookieOrHeaderJWTAuthentication"
    name = ["jwtBearerAuth", "jwtCookieAuth"]

    def get_security_requirement(self, _auto_schema):
        return [{"jwtBearerAuth": []}, {"jwtCookieAuth": []}]

    def get_security_definition(self, _auto_schema):
        return [
            {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT access token supplied in the Authorization header.",
            },
            {
                "type": "apiKey",
                "in": "cookie",
                "name": settings.JWT_ACCESS_COOKIE,
                "description": (
                    "JWT access token supplied in the HttpOnly access cookie."
                ),
            },
        ]
