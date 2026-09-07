from django.db.models import Max

from tournaments.domain.dice.categories import ScoreCategory
from tournaments.models import GameParticipant, Turn


def refresh_participant_completion(game_participant: GameParticipant) -> None:
    used_categories = set(
        game_participant.score_entries.values_list("category", flat=True)
    )

    game_participant.is_completed = len(used_categories) == len(ScoreCategory)


def activate_next_turn(current_turn: Turn) -> Turn | None:
    """Create the next turn in cyclic table order, skipping completed scorecards."""
    current_participant = current_turn.game_participant
    game = current_participant.game

    eligible = list(
        game.game_participants.filter(is_completed=False).order_by("turn_order", "pk")
    )

    if not eligible:
        return None

    next_participant = next(
        (
            participant
            for participant in eligible
            if participant.turn_order > current_participant.turn_order
        ),
        eligible[0],
    )

    last_number = next_participant.turns.aggregate(last=Max("number"))["last"] or 0

    return Turn.objects.create(
        game_participant=next_participant,
        number=last_number + 1,
    )
