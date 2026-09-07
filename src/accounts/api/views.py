from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import PlayerProfile
from accounts.serializers import PlayerProfileSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request: Request):
    profile = get_object_or_404(PlayerProfile, user=request.user)
    serializer = PlayerProfileSerializer(profile)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request: Request):
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return Response(
            {"refresh": ["This field is required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = RefreshToken(refresh_token)

        if str(token["user_id"]) != str(request.user.pk):
            return Response(
                {"refresh": ["Token does not belong to the authenticated user."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token.blacklist()
    except TokenError:
        return Response(
            {"refresh": ["Invalid or expired token."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)
