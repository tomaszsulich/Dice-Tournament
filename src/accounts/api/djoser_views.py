from djoser.views import UserViewSet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from api.schema import (
    AUTHENTICATED_COMMAND_ERROR_RESPONSES,
    INTERNAL_ERROR_RESPONSE,
    PERMISSION_ERROR_RESPONSE,
    THROTTLED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)


class DiceUserViewSet(UserViewSet):
    """Djoser account actions with the application's explicit OpenAPI refusals."""

    @extend_schema(
        responses={
            201: OpenApiTypes.OBJECT,
            400: VALIDATION_ERROR_RESPONSE,
            403: PERMISSION_ERROR_RESPONSE,
            429: THROTTLED_RESPONSE,
            500: INTERNAL_ERROR_RESPONSE,
        }
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)

    @extend_schema(
        responses={
            **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
            204: None,
            400: VALIDATION_ERROR_RESPONSE,
        }
    )
    def set_password(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data["new_password"]

        if request.user.check_password(new_password):
            raise ValidationError(
                {
                    "new_password": [
                        "New password must be different from the current password."
                    ]
                }
            )

        return super().set_password(request, *args, **kwargs)

    @extend_schema(
        responses={
            204: None,
            400: VALIDATION_ERROR_RESPONSE,
            403: PERMISSION_ERROR_RESPONSE,
            429: THROTTLED_RESPONSE,
            500: INTERNAL_ERROR_RESPONSE,
        }
    )
    def reset_password(self, request: Request, *args, **kwargs) -> Response:
        return super().reset_password(request, *args, **kwargs)

    @extend_schema(
        responses={
            204: None,
            400: VALIDATION_ERROR_RESPONSE,
            403: PERMISSION_ERROR_RESPONSE,
            429: THROTTLED_RESPONSE,
            500: INTERNAL_ERROR_RESPONSE,
        }
    )
    def reset_password_confirm(self, request: Request, *args, **kwargs) -> Response:
        return super().reset_password_confirm(request, *args, **kwargs)
