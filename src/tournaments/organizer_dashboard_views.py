from django.http import HttpResponse
from django.shortcuts import render
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from tournaments.selectors.organizer_dashboard import get_organizer_dashboard
from tournaments.selectors.participant_comparison import (
    InvalidComparison,
    compare_participant,
    get_comparison_options,
    get_participant_history_page,
)


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def organizer_dashboard_page(request: Request, tournament_id: int) -> HttpResponse:
    snapshot = get_organizer_dashboard(
        actor=request.user,
        tournament_id=tournament_id,
    )

    return render(
        request._request,
        "tournaments/organizer_dashboard.html",
        {"initial_dashboard": snapshot},
    )


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def organizer_dashboard_api(request: Request, tournament_id: int):
    return Response(
        get_organizer_dashboard(
            actor=request.user,
            tournament_id=tournament_id,
        )
    )


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participant_comparison_page(request: Request, participant_id: int) -> HttpResponse:
    options = get_comparison_options(actor=request.user, participant_id=participant_id)

    return render(
        request._request,
        "tournaments/participant_comparison.html",
        {"comparison_options": options},
    )


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="tournament_ids",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            many=True,
            required=True,
            description="One to four unique completed tournament IDs.",
        )
    ],
    responses=OpenApiTypes.OBJECT,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participant_comparison_api(request: Request, participant_id: int):
    raw_ids = request.query_params.getlist("tournament_ids")

    if len(raw_ids) == 1 and "," in raw_ids[0]:
        raw_ids = [item for item in raw_ids[0].split(",") if item]

    try:
        result = compare_participant(
            actor=request.user,
            participant_id=participant_id,
            tournament_ids=raw_ids,
        )

    except InvalidComparison as exc:
        return Response(
            {"code": "INVALID_COMPARISON", "detail": str(exc)},
            status=400,
        )

    return Response(result)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="tournament_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
        ),
    ],
    responses=OpenApiTypes.OBJECT,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participant_comparison_history_api(request: Request, participant_id: int):
    try:
        tournament_id = int(request.query_params.get("tournament_id", ""))
    except ValueError:
        return Response(
            {"code": "INVALID_COMPARISON", "detail": "Tournament ID is required."},
            status=400,
        )

    return Response(
        get_participant_history_page(
            actor=request.user,
            participant_id=participant_id,
            tournament_id=tournament_id,
            page_number=request.query_params.get("page", 1),
        )
    )
