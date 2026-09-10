from collections.abc import Callable, Mapping
from typing import Any

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from tournaments.domain.dice.categories import (
    SCHOOL_CATEGORIES,
    PokerScoringVariant,
    ScoreCategory,
)
from tournaments.domain.dice.context import DiceContext, ScoringConfig, ScoringContext
from tournaments.domain.dice.result import (
    FigureStrikeOffResult,
    PointsResult,
    SchoolSuccessResult,
    ScoringResult,
)
from tournaments.domain.dice.scoring import (
    AmbiguousFigureSelectionError,
    InvalidFigureSelectionError,
    InvalidScoreSelectionError,
    apply_school_penalty,
    figure_completion_bonus,
    score,
)
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import ParticipantStatus, TournamentStatus
from tournaments.models import (
    Game,
    GameParticipant,
    IdempotencyRecord,
    ScoreEntry,
    ScoreResultKind,
    Turn,
)
from tournaments.services.dice.advance_turn import (
    activate_next_turn,
    refresh_participant_completion,
)
from tournaments.services.idempotency import (
    CATEGORY_COMMAND,
    canonicalize_payload,
    find_idempotency_record,
    hash_payload,
    replay_or_raise_conflict,
)

type Publisher = Callable[[str, dict[str, int]], None]

BONUS_REQUIRED_CATEGORIES = frozenset(ScoreCategory) - SCHOOL_CATEGORIES


class CategoryCommandError(Exception):
    code = "CATEGORY_COMMAND_ERROR"


class GameNotFound(CategoryCommandError):
    code = "GAME_NOT_FOUND"


class CategoryForbidden(CategoryCommandError):
    code = "NOT_YOUR_TURN"


class CategoryUnavailable(CategoryCommandError):
    code = "CATEGORY_UNAVAILABLE"


class CategoryAlreadyUsed(CategoryCommandError):
    code = "CATEGORY_ALREADY_USED"


class InvalidCategorySelection(CategoryCommandError):
    code = "INVALID_CATEGORY_SELECTION"


def select_category(
    *,
    user: User,
    game_id: int,
    payload: Mapping[str, Any],
    key: str,
    publisher: Publisher,
) -> dict[str, Any]:
    if not getattr(user, "is_authenticated", False):
        raise CategoryForbidden

    canonical = canonicalize_payload(payload)
    fingerprint = hash_payload(canonical)

    existing = find_idempotency_record(
        user=user,
        game_id=game_id,
        key=key,
        command=CATEGORY_COMMAND,
    )

    if existing is not None:
        return replay_or_raise_conflict(existing, fingerprint)

    with transaction.atomic():
        _lock_game(game_id)

        existing = find_idempotency_record(
            user=user,
            game_id=game_id,
            key=key,
            command=CATEGORY_COMMAND,
        )

        if existing is not None:
            return replay_or_raise_conflict(existing, fingerprint)

        turn = _lock_current_turn(game_id)
        _require_legal_selection(turn, user)

        try:
            category = ScoreCategory(canonical["category"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidCategorySelection from exc

        if set(canonical) - {"category", "pair_value"}:
            raise InvalidCategorySelection

        pair_value = canonical.get("pair_value")
        participant = turn.game_participant

        if participant.score_entries.filter(category=category).exists():
            raise CategoryAlreadyUsed

        last_roll = turn.rolls.order_by("roll_number").last()

        if last_roll is None:
            raise CategoryUnavailable

        context = ScoringContext(
            dice=DiceContext.from_values(last_roll.values),
            roll_number=last_roll.roll_number,
            config=ScoringConfig(
                poker_variant=PokerScoringVariant(
                    participant.game.round.tournament.poker_scoring_variant
                )
            ),
        )

        try:
            result = score(category, context, pair_value=pair_value)
        except (
            AmbiguousFigureSelectionError,
            InvalidFigureSelectionError,
            InvalidScoreSelectionError,
        ) as exc:
            raise InvalidCategorySelection from exc

        entry = _create_score_entry(turn, category, result)
        turn.completed_at = timezone.now()
        turn.save(update_fields=["completed_at"])

        _refresh_score_aggregates(participant)
        refresh_participant_completion(participant)

        participant.save(
            update_fields=[
                "is_completed",
                "raw_score",
                "school_balance",
                "figure_points",
                "bonus_points",
                "final_score",
            ]
        )

        next_turn = activate_next_turn(turn)
        response = _serialize_response(entry, participant, next_turn)

        IdempotencyRecord.objects.create(
            user=user,
            game_id=game_id,
            command=CATEGORY_COMMAND,
            key=key,
            fingerprint=fingerprint,
            response=response,
        )

        event_payload = {
            "game_id": game_id,
            "turn_id": turn.pk,
            "score_entry_id": entry.pk,
        }

        if next_turn is not None:
            event_payload["next_turn_id"] = next_turn.pk

        transaction.on_commit(lambda: publisher("table_changed", event_payload))

        return response


def _lock_game(game_id: int) -> Game:
    try:
        return Game.objects.select_for_update().get(pk=game_id)
    except Game.DoesNotExist as exc:
        raise GameNotFound from exc


def _lock_current_turn(game_id: int) -> Turn:
    turn = (
        Turn.objects.select_for_update()
        .select_related(
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

    if turn is None:
        raise CategoryUnavailable

    return turn


def _require_legal_selection(turn: Turn, user: User) -> None:
    participant = turn.game_participant
    owner = participant.tournament_participant.player_profile.user
    tournament = participant.game.round.tournament

    if owner.pk != user.pk:
        raise CategoryForbidden

    if (
        tournament.status != TournamentStatus.ACTIVE
        or participant.game.round.status != RoundStatus.ACTIVE
        or participant.tournament_participant.status != ParticipantStatus.ACTIVE
    ):
        raise CategoryUnavailable

    if hasattr(turn, "score_entry") or not turn.rolls.exists():
        raise CategoryUnavailable


def _create_score_entry(
    turn: Turn,
    category: ScoreCategory,
    result: ScoringResult,
) -> ScoreEntry:
    if isinstance(result, PointsResult):
        result_kind = ScoreResultKind.POINTS
        value = result.points

    elif isinstance(result, SchoolSuccessResult):
        result_kind = ScoreResultKind.SCHOOL_BALANCE
        value = result.balance

    elif isinstance(result, FigureStrikeOffResult):
        result_kind = ScoreResultKind.STRIKE_OFF
        value = None

    else:
        raise TypeError(f"Unsupported scoring result: {type(result)!r}")

    return ScoreEntry.objects.create(
        turn=turn,
        game_participant=turn.game_participant,
        category=category,
        result_kind=result_kind,
        value=value,
    )


def _refresh_score_aggregates(participant: GameParticipant) -> None:
    entries = list(participant.score_entries.all())
    used = {ScoreCategory(entry.category) for entry in entries}

    school_balance = sum(
        entry.value or 0
        for entry in entries
        if ScoreCategory(entry.category) in SCHOOL_CATEGORIES
    )

    figure_points = sum(
        entry.value or 0
        for entry in entries
        if ScoreCategory(entry.category) not in SCHOOL_CATEGORIES
    )

    raw_score = school_balance + figure_points

    school_adjustment = 0

    if SCHOOL_CATEGORIES <= used:
        school_adjustment = apply_school_penalty(school_balance) - school_balance

    bonus_required_entries = [
        entry
        for entry in entries
        if ScoreCategory(entry.category) in BONUS_REQUIRED_CATEGORIES
    ]

    figure_bonus = figure_completion_bonus(
        all_completed=BONUS_REQUIRED_CATEGORIES <= used,
        has_strike_off=any(
            entry.result_kind == ScoreResultKind.STRIKE_OFF
            for entry in bonus_required_entries
        ),
    )

    participant.school_balance = school_balance
    participant.figure_points = figure_points
    participant.raw_score = raw_score
    participant.bonus_points = school_adjustment + figure_bonus
    participant.final_score = raw_score + participant.bonus_points


def _serialize_response(
    entry: ScoreEntry,
    participant: GameParticipant,
    next_turn: Turn | None,
) -> dict[str, Any]:
    return {
        "score_entry": {
            "id": entry.pk,
            "turn_id": entry.turn_id,
            "category": entry.category,
            "result_kind": entry.result_kind,
            "value": entry.value,
        },
        "participant_score": {
            "game_participant_id": participant.pk,
            "raw_score": participant.raw_score,
            "school_balance": participant.school_balance,
            "figure_points": participant.figure_points,
            "bonus_points": participant.bonus_points,
            "final_score": participant.final_score,
            "is_completed": participant.is_completed,
        },
        "next_turn_id": next_turn.pk if next_turn is not None else None,
        "game_complete": next_turn is None,
    }
