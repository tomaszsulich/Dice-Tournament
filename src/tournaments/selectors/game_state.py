from collections import Counter

from accounts.models import User
from tournaments.domain.dice.categories import (
    FIGURES_SECTION_INFORMATION,
    SCHOOL_SECTION_INFORMATION,
    ScoreCategory,
)
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import ParticipantStatus, TournamentStatus
from tournaments.models import Game, Roll, ScoreEntry, ScoreResultKind, Turn


def _pair_selection_options(latest_roll: Roll | None) -> list[int]:
    if latest_roll is None:
        return []

    return sorted(
        value for value, count in Counter(latest_roll.values).items() if count >= 2
    )


def _score_value(entry: ScoreEntry | None) -> int | str | None:
    if entry is None:
        return None

    if entry.result_kind == ScoreResultKind.STRIKE_OFF:
        return "X"

    if entry.result_kind == ScoreResultKind.SCHOOL_BALANCE and entry.value == 0:
        return "X"

    return entry.value


def get_game_snapshot(*, game: Game, user: User) -> dict[str, object]:
    """Build the authoritative table snapshot consumed by REST and the template UI."""
    participants = list(
        game.game_participants.select_related(
            "tournament_participant__player_profile__user"
        )
        .prefetch_related("score_entries")
        .order_by("turn_order")
    )

    turn = (
        Turn.objects.select_related(
            "game_participant__tournament_participant__player_profile__user"
        )
        .select_related("score_entry")
        .prefetch_related("rolls")
        .filter(game_participant__game=game, completed_at__isnull=True)
        .order_by("game_participant__turn_order", "number", "pk")
        .first()
    )

    latest_roll = turn.rolls.order_by("roll_number").last() if turn else None
    roll_count = turn.rolls.count() if turn else 0

    active_user_id = (
        turn.game_participant.tournament_participant.player_profile.user_id
        if turn
        else None
    )

    current_turn_available = bool(
        turn
        and active_user_id == user.pk
        and game.round.tournament.status == TournamentStatus.ACTIVE
        and game.round.status == RoundStatus.ACTIVE
        and turn.game_participant.tournament_participant.status
        == ParticipantStatus.ACTIVE
        and turn.completed_at is None
        and not hasattr(turn, "score_entry")
    )

    can_roll = current_turn_available and roll_count < 3
    can_hold = current_turn_available and 0 < roll_count < 3

    used_categories = (
        {entry.category for entry in turn.game_participant.score_entries.all()}
        if turn and current_turn_available
        else set()
    )

    selectable_category_ids = (
        [
            category.value
            for category in ScoreCategory
            if roll_count > 0 and category.value not in used_categories
        ]
        if current_turn_available
        else []
    )

    participant_rows = []

    for participant in participants:
        entries = {entry.category: entry for entry in participant.score_entries.all()}

        participant_rows.append(
            {
                "id": participant.pk,
                "name": participant.tournament_participant.display_name_snapshot,
                "is_current_user": (
                    participant.tournament_participant.player_profile.user_id == user.pk
                ),
                "is_active": participant.pk
                == getattr(turn, "game_participant_id", None),
                "total_score": participant.final_score,
                "scores": {
                    category.value: _score_value(entries.get(category.value))
                    for category in ScoreCategory
                },
            }
        )

    current_participation = next(
        (
            participant.tournament_participant
            for participant in participants
            if participant.tournament_participant.player_profile.user_id == user.pk
        ),
        None,
    )

    participation_ongoing = bool(
        current_participation
        and current_participation.status == ParticipantStatus.ACTIVE
        and game.round.tournament.status == TournamentStatus.ACTIVE
    )

    return {
        "game_id": game.pk,
        "state_version": game.state_version,
        "event_mode": game.round.tournament.event_mode,
        "game_complete": bool(participants)
        and all(participant.is_completed for participant in participants),
        "participation_ongoing": participation_ongoing,
        "participants": participant_rows,
        "category_sections": {
            "school": {
                "label": "School",
                "information": SCHOOL_SECTION_INFORMATION,
            },
            "figures": {
                "label": "Figures",
                "information": FIGURES_SECTION_INFORMATION,
            },
        },
        "categories": [
            {
                "id": category.value,
                "label": category.label,
                "information": category.information,
                "selection_options": (
                    _pair_selection_options(latest_roll)
                    if category is ScoreCategory.PAIR
                    else []
                ),
            }
            for category in ScoreCategory
        ],
        "turn": (
            {
                "id": turn.pk,
                "number": turn.number,
                "roll_count": roll_count,
                "can_roll": can_roll,
                "can_hold": can_hold,
                "selectable_category_ids": selectable_category_ids,
                "held_dice": list(turn.held_dice),
                "dice": list(latest_roll.values) if latest_roll else [None] * 5,
                "dice_total": sum(latest_roll.values) if latest_roll else None,
                "rerolls_remaining": max(0, 3 - roll_count) if roll_count else None,
                "is_current_user": active_user_id == user.pk,
                "category_required": roll_count >= 3,
                "action_deadline": (
                    turn.action_deadline.isoformat()
                    if turn.action_deadline is not None
                    else None
                ),
            }
            if turn
            else None
        ),
    }
