from drf_spectacular.utils import OpenApiExample, OpenApiResponse

DOMAIN_ERROR_EXAMPLE = OpenApiExample(
    "Domain error",
    value={
        "code": "NOT_YOUR_TURN",
        "message": "This action is not available outside your turn.",
    },
    response_only=True,
)

DOMAIN_ERROR_RESPONSE = OpenApiResponse(
    description="Domain error response with a stable machine-readable code.",
    examples=[DOMAIN_ERROR_EXAMPLE],
)
