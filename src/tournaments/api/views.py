from secrets import SystemRandom

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, Q
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import PlayerProfile
from api.schema import (
    AUTHENTICATED_COMMAND_ERROR_RESPONSES,
    AUTHENTICATED_ERROR_RESPONSES,
    DOMAIN_ERROR_RESPONSE,
    PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    VALIDATION_OR_DOMAIN_ERROR_RESPONSE,
)
from common.errors import domain_error
from tournaments.api.schema import (
    ChooseCategoryResultSerializer,
    GameStateResultSerializer,
    HoldResultSerializer,
    RollResultSerializer,
    RoundBarrierResultSerializer,
    RoundDrawResultSerializer,
    TournamentDetailResultSerializer,
    TournamentLifecycleResultSerializer,
    TournamentRankingRowSerializer,
)
from tournaments.domain.tournament.types import (
    ParticipantStatus,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Game, Round, Tournament, TournamentParticipant
from tournaments.realtime.publisher import publish_realtime_event
from tournaments.selectors.game_state import get_game_snapshot
from tournaments.serializers.lifecycle import (
    DrawCommandSerializer,
    EmptyLifecycleCommandSerializer,
)
from tournaments.serializers.management import (
    OrganizerParticipantCommandSerializer,
    TournamentCreateSerializer,
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
)
from tournaments.services.connection_state import official_game_for_participant
from tournaments.services.dice.hold_dice import (
    GameNotFound as HoldGameNotFound,
)
from tournaments.services.dice.hold_dice import (
    HoldForbidden,
    HoldUnavailable,
    HoldUnchanged,
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
    add_participant_by_organizer,
    join_tournament,
    leave_tournament,
)
from tournaments.services.round_barrier import (
    evaluate_round_barrier,
    get_tournament_ranking,
)
from tournaments.services.tournament_lifecycle import (
    close_registration,
    complete_tournament,
    create_tournament,
    open_registration,
    start_tournament,
)


def _validate_empty_command(request: Request):
    serializer = EmptyRegistrationCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return None


@extend_schema(
    operation_id="tournaments_create",
    request=TournamentCreateSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        201: TournamentDetailResultSerializer,
        400: VALIDATION_ERROR_RESPONSE,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tournament_create(request: Request):
    serializer = TournamentCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        tournament = create_tournament(
            organizer=request.user,
            **serializer.validated_data,
        )
    except ValidationError as exc:
        return Response(
            getattr(exc, "message_dict", {"detail": exc.messages}),
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"id": tournament.pk, "name": tournament.name, "status": tournament.status},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    operation_id="tournaments_list_available",
    parameters=[
        OpenApiParameter(
            name="available_to_join",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            required=True,
            description=(
                "Must be true. Returns tournaments currently available to join."
            ),
        )
    ],
    responses={
        **AUTHENTICATED_ERROR_RESPONSES,
        200: OpenTournamentSerializer(many=True),
        400: VALIDATION_ERROR_RESPONSE,
    },
)
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


@extend_schema(
    request=EmptyRegistrationCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        201: TournamentParticipantSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
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


@extend_schema(
    request=EmptyRegistrationCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: TournamentParticipantSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
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


@extend_schema(
    request=RollCommandSerializer,
    parameters=[
        OpenApiParameter(
            name="Idempotency-Key",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Unique key for safely retrying the same roll command.",
        )
    ],
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        201: RollResultSerializer,
        400: VALIDATION_OR_DOMAIN_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
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
            publisher=publish_realtime_event,
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


@extend_schema(
    request=HoldDiceCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: HoldResultSerializer,
        400: VALIDATION_OR_DOMAIN_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
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
            publisher=publish_realtime_event,
        )
    except HoldGameNotFound as exc:
        return domain_error(exc.code, status.HTTP_404_NOT_FOUND)
    except HoldForbidden as exc:
        return domain_error(exc.code, status.HTTP_403_FORBIDDEN)
    except InvalidHoldPayload as exc:
        return domain_error(exc.code, status.HTTP_400_BAD_REQUEST)
    except (HoldUnavailable, HoldUnchanged) as exc:
        return domain_error(exc.code, status.HTTP_409_CONFLICT)

    return Response(response, status=status.HTTP_200_OK)


@extend_schema(
    request=ChooseCategoryCommandSerializer,
    parameters=[
        OpenApiParameter(
            name="Idempotency-Key",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Unique key for safely retrying the same category command.",
        )
    ],
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        201: ChooseCategoryResultSerializer,
        400: VALIDATION_OR_DOMAIN_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
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
            publisher=publish_realtime_event,
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


@extend_schema(
    responses={
        **AUTHENTICATED_ERROR_RESPONSES,
        200: GameStateResultSerializer,
        403: DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_state(request: Request, game_id: int):
    try:
        game = Game.objects.select_related("round__tournament").get(pk=game_id)
    except Game.DoesNotExist:
        return domain_error("GAME_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    is_organizer = game.round.tournament.organizers.filter(pk=request.user.pk).exists()

    if not is_organizer:
        participant = (
            TournamentParticipant.objects.filter(
                tournament=game.round.tournament,
                player_profile__user=request.user,
            )
            .select_related("player_profile")
            .first()
        )

        if participant is None:
            return domain_error("GAME_FORBIDDEN", status.HTTP_403_FORBIDDEN)

        if participant.status != ParticipantStatus.ACTIVE:
            return domain_error("PARTICIPATION_INACTIVE", status.HTTP_403_FORBIDDEN)

        official_game = official_game_for_participant(participant)

        if official_game is None:
            return domain_error("GAME_FORBIDDEN", status.HTTP_403_FORBIDDEN)

        if official_game.pk != game.pk:
            return Response(
                {
                    "code": "TABLE_ASSIGNMENT_CHANGED",
                    "table_id": official_game.pk,
                    "target_url": reverse(
                        "participant-table",
                        args=(official_game.pk,),
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

    return Response(
        get_game_snapshot(game=game, user=request.user),
        status=status.HTTP_200_OK,
    )


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


@extend_schema(
    operation_id="tournaments_retrieve",
    responses={
        **AUTHENTICATED_ERROR_RESPONSES,
        200: TournamentDetailResultSerializer,
        403: DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
    },
)
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


@extend_schema(
    request=EmptyLifecycleCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: TournamentLifecycleResultSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
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


@extend_schema(
    request=EmptyLifecycleCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: TournamentLifecycleResultSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tournament_close_registration(request: Request, tournament_id: int):
    tournament, error = _organizer_tournament(request, tournament_id)

    if error is not None:
        return error

    serializer = EmptyLifecycleCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        tournament = close_registration(tournament)
    except ValidationError:
        return domain_error(
            "TOURNAMENT_TRANSITION_UNAVAILABLE", status.HTTP_409_CONFLICT
        )

    return Response({"id": tournament.pk, "status": tournament.status})


@extend_schema(
    request=OrganizerParticipantCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        201: TournamentParticipantSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tournament_add_participant(request: Request, tournament_id: int):
    tournament, error = _organizer_tournament(request, tournament_id)

    if error is not None:
        return error

    serializer = OrganizerParticipantCommandSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = PlayerProfile.objects.get(
            pk=serializer.validated_data["player_profile_id"]
        )
    except PlayerProfile.DoesNotExist:
        return domain_error("PLAYER_PROFILE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

    try:
        participant = add_participant_by_organizer(
            tournament_id=tournament.pk,
            player_profile=profile,
            team_label=serializer.validated_data.get("team_label", ""),
            starting_number=serializer.validated_data.get("starting_number"),
            seeding=serializer.validated_data.get("seeding"),
        )
    except (AlreadyRegistered, RegistrationUnavailable, TournamentFull) as exc:
        return domain_error(exc.code, status.HTTP_409_CONFLICT)
    except ValidationError as exc:
        return Response(
            getattr(exc, "message_dict", {"detail": exc.messages}),
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        TournamentParticipantSerializer(participant).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    request=EmptyLifecycleCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: TournamentLifecycleResultSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
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
        tournament = start_tournament(
            tournament,
            publisher=publish_realtime_event,
        )
    except ValidationError:
        return domain_error(
            "TOURNAMENT_TRANSITION_UNAVAILABLE", status.HTTP_409_CONFLICT
        )

    return Response({"id": tournament.pk, "status": tournament.status})


@extend_schema(
    request=EmptyLifecycleCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: TournamentLifecycleResultSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
)
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


@extend_schema(
    responses={
        **AUTHENTICATED_ERROR_RESPONSES,
        200: TournamentRankingRowSerializer(many=True),
        403: DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
    }
)
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


@extend_schema(
    request=EmptyLifecycleCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: RoundBarrierResultSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
    },
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
        publisher=publish_realtime_event,
    )

    return Response(
        {
            "state": result.state,
            "round_id": result.round_id,
            "tied_participant_ids": result.tied_participant_ids,
        }
    )


@extend_schema(
    request=DrawCommandSerializer,
    responses={
        **AUTHENTICATED_COMMAND_ERROR_RESPONSES,
        200: RoundDrawResultSerializer,
        400: VALIDATION_ERROR_RESPONSE,
        403: PERMISSION_OR_DOMAIN_ERROR_RESPONSE,
        404: DOMAIN_ERROR_RESPONSE,
        409: DOMAIN_ERROR_RESPONSE,
    },
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
