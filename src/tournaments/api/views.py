from secrets import SystemRandom

from django.db.models import Count, F, Q
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tournaments.domain.tournament.types import (
    ParticipantStatus,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Tournament
from tournaments.serializers.participants import TournamentParticipantSerializer
from tournaments.serializers.registration import (
    EmptyRegistrationCommandSerializer,
    OpenTournamentSerializer,
)
from tournaments.serializers.roll import RollCommandSerializer
from tournaments.services.dice.roll_dice import (
    GameNotFound,
    InvalidRollPayload,
    RollForbidden,
    RollUnavailable,
    execute_roll,
)
from tournaments.services.idempotency import IdempotencyConflict
from tournaments.services.participants import (
    AlreadyRegistered,
    ParticipationNotFound,
    PlayerProfileRequired,
    RegistrationUnavailable,
    SelfRegistrationForbidden,
    SelfWithdrawalUnavailable,
    TournamentFull,
    join_tournament,
    leave_tournament,
)


def _domain_error(code: str, response_status: int):
    return Response(
        {"code": code},
        status=response_status,
    )


def _validate_empty_command(request: HttpRequest):
    serializer = EmptyRegistrationCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tournament_list(request: HttpRequest):
    if request.query_params.get("available_to_join") != "true":
        return Response(
            {"available_to_join": ["Only 'true' is supported in this endpoint."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()

    tournaments = (
        Tournament.objects.filter(
            status=TournamentStatus.REGISTRATION,
            registration_mode=RegistrationMode.OPEN,
            registration_closed_at__isnull=True,
        )
        .filter(
            Q(registration_deadline__isnull=True) | Q(registration_deadline__gt=now)
        )
        .annotate(
            registered_count=Count(
                "tournament_participants",
                filter=Q(tournament_participants__status=ParticipantStatus.REGISTERED),
            )
        )
        .filter(registered_count__lt=F("max_participants"))
        .order_by("registration_deadline", "id")
    )

    serializer = OpenTournamentSerializer(tournaments, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join(request: HttpRequest, tournament_id: int):
    invalid_payload_response = _validate_empty_command(request)

    if invalid_payload_response is not None:
        return invalid_payload_response

    try:
        participant = join_tournament(
            tournament_id=tournament_id,
            user=request.user,
        )
    except Tournament.DoesNotExist:
        return _domain_error("TOURNAMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    except SelfRegistrationForbidden as exc:
        return _domain_error(exc.code, status.HTTP_403_FORBIDDEN)
    except ParticipationNotFound as exc:
        return _domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except (
        AlreadyRegistered,
        PlayerProfileRequired,
        RegistrationUnavailable,
        TournamentFull,
    ) as exc:
        return _domain_error(exc.code, status.HTTP_409_CONFLICT)

    serializer = TournamentParticipantSerializer(participant)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave(request: HttpRequest, tournament_id: int):
    invalid_payload_response = _validate_empty_command(request)

    if invalid_payload_response is not None:
        return invalid_payload_response

    try:
        participant = leave_tournament(
            tournament_id=tournament_id,
            user=request.user,
        )
    except Tournament.DoesNotExist:
        return _domain_error("TOURNAMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    except ParticipationNotFound as exc:
        return _domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except (PlayerProfileRequired, SelfWithdrawalUnavailable) as exc:
        return _domain_error(exc.code, status.HTTP_409_CONFLICT)

    serializer = TournamentParticipantSerializer(participant)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def roll_game(request: HttpRequest, game_id: int):
    key = request.headers.get("Idempotency-Key")

    if not key or len(key) > 128:
        return Response(
            {"idempotency_key": ["A valid Idempotency-Key header is required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = RollCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        response = execute_roll(
            user=request.user,
            game_id=game_id,
            payload=serializer.validated_data,
            key=key,
            rng=SystemRandom(),
            publisher=lambda _event, _payload: None,
        )
    except GameNotFound as exc:
        return _domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except RollForbidden as exc:
        return _domain_error(exc.code, status.HTTP_403_FORBIDDEN)
    except InvalidRollPayload as exc:
        return _domain_error(exc.code, status.HTTP_400_BAD_REQUEST)
    except (IdempotencyConflict, RollUnavailable) as exc:
        return _domain_error(exc.code, status.HTTP_409_CONFLICT)

    return Response(response, status=status.HTTP_201_CREATED)
