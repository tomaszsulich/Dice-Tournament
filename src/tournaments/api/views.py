from secrets import SystemRandom

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from common.errors import domain_error
from tournaments.domain.tournament.types import (
    ParticipantStatus,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Game, Round, Tournament, Turn
from tournaments.serializers.lifecycle import (
    DrawCommandSerializer,
    EmptyLifecycleCommandSerializer,
)
from tournaments.serializers.participants import TournamentParticipantSerializer
from tournaments.serializers.registration import (
    EmptyRegistrationCommandSerializer,
    OpenTournamentSerializer,
)
from tournaments.serializers.roll import RollCommandSerializer
from tournaments.serializers.turn_flow import (
    ChooseCategoryCommandSerializer,
    HoldDiceCommandSerializer,
    TurnStateSerializer,
)
from tournaments.services.dice.hold_dice import (
    GameNotFound as HoldGameNotFound,
)
from tournaments.services.dice.hold_dice import (
    HoldForbidden,
    HoldUnavailable,
    InvalidHoldPayload,
    set_held_dice,
)
from tournaments.services.dice.roll_dice import (
    GameNotFound,
    InvalidRollPayload,
    RollForbidden,
    RollUnavailable,
    execute_roll,
)
from tournaments.services.dice.select_category import (
    CategoryAlreadyUsed,
    CategoryForbidden,
    CategoryUnavailable,
    InvalidCategorySelection,
    select_category,
)
from tournaments.services.dice.select_category import (
    GameNotFound as CategoryGameNotFound,
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
from tournaments.services.round_barrier import (
    evaluate_round_barrier,
    get_tournament_ranking,
)
from tournaments.services.tournament_lifecycle import (
    complete_tournament,
    open_registration,
    start_tournament,
)


def _validate_empty_command(request: Request):
    serializer = EmptyRegistrationCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tournament_list(request: Request):
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
def join(request: Request, tournament_id: int):
    invalid_payload_response = _validate_empty_command(request)

    if invalid_payload_response is not None:
        return invalid_payload_response

    try:
        participant = join_tournament(
            tournament_id=tournament_id,
            user=request.user,
        )
    except Tournament.DoesNotExist:
        return domain_error("TOURNAMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    except SelfRegistrationForbidden as exc:
        return domain_error(exc.code, status.HTTP_403_FORBIDDEN)
    except ParticipationNotFound as exc:
        return domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except (
        AlreadyRegistered,
        PlayerProfileRequired,
        RegistrationUnavailable,
        TournamentFull,
    ) as exc:
        return domain_error(exc.code, status.HTTP_409_CONFLICT)

    serializer = TournamentParticipantSerializer(participant)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave(request: Request, tournament_id: int):
    invalid_payload_response = _validate_empty_command(request)

    if invalid_payload_response is not None:
        return invalid_payload_response

    try:
        participant = leave_tournament(
            tournament_id=tournament_id,
            user=request.user,
        )
    except Tournament.DoesNotExist:
        return domain_error("TOURNAMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)
    except ParticipationNotFound as exc:
        return domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except (PlayerProfileRequired, SelfWithdrawalUnavailable) as exc:
        return domain_error(exc.code, status.HTTP_409_CONFLICT)

    serializer = TournamentParticipantSerializer(participant)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def roll_game(request: Request, game_id: int):
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
        return domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except RollForbidden as exc:
        return domain_error(exc.code, status.HTTP_403_FORBIDDEN)
    except InvalidRollPayload as exc:
        return domain_error(exc.code, status.HTTP_400_BAD_REQUEST)
    except (IdempotencyConflict, RollUnavailable) as exc:
        return domain_error(exc.code, status.HTTP_409_CONFLICT)

    return Response(response, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def hold_game_dice(request: Request, game_id: int):
    serializer = HoldDiceCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        response = set_held_dice(
            user=request.user,
            game_id=game_id,
            held_flags=tuple(serializer.validated_data["held"]),
            publisher=lambda _event, _payload: None,
        )
    except HoldGameNotFound as exc:
        return domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except HoldForbidden as exc:
        return domain_error(exc.code, status.HTTP_403_FORBIDDEN)
    except InvalidHoldPayload as exc:
        return domain_error(exc.code, status.HTTP_400_BAD_REQUEST)
    except HoldUnavailable as exc:
        return domain_error(exc.code, status.HTTP_409_CONFLICT)

    return Response(response, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def choose_game_category(request: Request, game_id: int):
    key = request.headers.get("Idempotency-Key")

    if not key or len(key) > 128:
        return Response(
            {"idempotency_key": ["A valid Idempotency-Key header is required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ChooseCategoryCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        response = select_category(
            user=request.user,
            game_id=game_id,
            payload=serializer.validated_data,
            key=key,
            publisher=lambda _event, _payload: None,
        )
    except CategoryGameNotFound as exc:
        return domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except CategoryForbidden as exc:
        return domain_error(exc.code, status.HTTP_403_FORBIDDEN)
    except InvalidCategorySelection as exc:
        return domain_error(exc.code, status.HTTP_400_BAD_REQUEST)
    except (CategoryAlreadyUsed, CategoryUnavailable, IdempotencyConflict) as exc:
        return domain_error(exc.code, status.HTTP_409_CONFLICT)

    return Response(response, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_state(request: Request, game_id: int):
    try:
        game = Game.objects.select_related("round__tournament").get(pk=game_id)
    except Game.DoesNotExist:
        return domain_error("GAME_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    is_table_participant = game.game_participants.filter(
        tournament_participant__player_profile__user=request.user
    ).exists()

    is_organizer = game.round.tournament.organizers.filter(pk=request.user.pk).exists()

    if not (is_table_participant or is_organizer):
        return domain_error("GAME_FORBIDDEN", status.HTTP_403_FORBIDDEN)

    turn = (
        Turn.objects.select_related(
            "game_participant__tournament_participant__player_profile__user",
            "game_participant__game__round__tournament",
        )
        .filter(
            game_participant__game_id=game_id,
            completed_at__isnull=True,
        )
        .order_by("game_participant__turn_order", "number", "pk")
        .first()
    )

    game_complete = (
        game.game_participants.exists()
        and not game.game_participants.filter(is_completed=False).exists()
    )

    data = {
        "game_id": game_id,
        "game_complete": game_complete,
        "turn": (
            TurnStateSerializer(turn, context={"user": request.user}).data
            if turn is not None
            else None
        ),
    }

    return Response(data, status=status.HTTP_200_OK)


def _organizer_tournament(
    request: Request, tournament_id: int
) -> tuple[Tournament, None] | tuple[None, Response]:
    try:
        tournament = Tournament.objects.get(pk=tournament_id)
    except Tournament.DoesNotExist:
        return None, domain_error("TOURNAMENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    if not tournament.organizers.filter(pk=request.user.pk).exists():
        return None, domain_error("TOURNAMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)

    return tournament, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tournament_detail(request: Request, tournament_id: int):
    tournament, error = _organizer_tournament(request, tournament_id)

    if error is not None:
        return error

    return Response(
        {"id": tournament.pk, "name": tournament.name, "status": tournament.status},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tournament_open_registration(request: Request, tournament_id: int):
    tournament, error = _organizer_tournament(request, tournament_id)

    if error is not None:
        return error

    serializer = EmptyLifecycleCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        tournament = open_registration(tournament)
    except ValidationError:
        return domain_error(
            "TOURNAMENT_TRANSITION_UNAVAILABLE", status.HTTP_409_CONFLICT
        )

    return Response({"id": tournament.pk, "status": tournament.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tournament_start(request: Request, tournament_id: int):
    tournament, error = _organizer_tournament(request, tournament_id)

    if error is not None:
        return error

    serializer = EmptyLifecycleCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        tournament = start_tournament(tournament)
    except ValidationError:
        return domain_error(
            "TOURNAMENT_TRANSITION_UNAVAILABLE", status.HTTP_409_CONFLICT
        )

    return Response({"id": tournament.pk, "status": tournament.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tournament_complete(request: Request, tournament_id: int):
    tournament, error = _organizer_tournament(request, tournament_id)

    if error is not None:
        return error

    serializer = EmptyLifecycleCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        tournament = complete_tournament(tournament)
    except ValidationError:
        return domain_error(
            "TOURNAMENT_TRANSITION_UNAVAILABLE", status.HTTP_409_CONFLICT
        )

    return Response({"id": tournament.pk, "status": tournament.status})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tournament_ranking(request: Request, tournament_id: int):
    tournament, error = _organizer_tournament(request, tournament_id)

    if error is not None:
        return error

    ranking = get_tournament_ranking(tournament.pk)

    return Response(
        [
            {
                "position": row.position,
                "participant_id": row.participant_id,
                "total_score": row.total_score,
                "round_scores": row.round_scores,
            }
            for row in ranking
        ]
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def round_barrier(request: Request, round_id: int):
    try:
        round_ = Round.objects.select_related("tournament").get(pk=round_id)
    except Round.DoesNotExist:
        return domain_error("ROUND_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    if not round_.tournament.organizers.filter(pk=request.user.pk).exists():
        return domain_error("TOURNAMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)

    serializer = EmptyLifecycleCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = evaluate_round_barrier(
        round_id=round_id,
        publisher=lambda _event, _payload: None,
    )

    return Response(
        {
            "state": result.state,
            "round_id": result.round_id,
            "tied_participant_ids": result.tied_participant_ids,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def round_draw(request: Request, round_id: int):
    try:
        round_ = Round.objects.select_related("tournament").get(pk=round_id)
    except Round.DoesNotExist:
        return domain_error("ROUND_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    if not round_.tournament.organizers.filter(pk=request.user.pk).exists():
        return domain_error("TOURNAMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)

    serializer = DrawCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = evaluate_round_barrier(
            round_id=round_id,
            publisher=lambda _event, _payload: None,
            organizer=request.user,
            draw_reason=serializer.validated_data["reason"],
            force_draw=True,
        )

    except PermissionDenied:
        return domain_error("TOURNAMENT_FORBIDDEN", status.HTTP_403_FORBIDDEN)

    except ValidationError:
        return domain_error("DRAW_UNAVAILABLE", status.HTTP_409_CONFLICT)

    if result.state != "drawn":
        return domain_error("DRAW_UNAVAILABLE", status.HTTP_409_CONFLICT)

    return Response(
        {
            "state": result.state,
            "round_id": result.round_id,
            "selected_participant_id": result.selected_participant_id,
        }
    )
