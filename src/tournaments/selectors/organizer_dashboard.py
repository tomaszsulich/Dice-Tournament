from __future__ import annotations

from datetime import datetime

from django.db.models import Count, Max, Prefetch, Q
from django.http import Http404
from django.utils import timezone

from accounts.models import User
from tournaments.domain.tournament.rounds import RoundStatus
from tournaments.domain.tournament.types import ParticipantConnectionStatus
from tournaments.models import Game, GameParticipant, Tournament, Turn


def _scoped_tournament(*, actor: User, tournament_id: int) -> Tournament:
    try:
        return Tournament.objects.filter(organizers=actor).get(pk=tournament_id)
    except Tournament.DoesNotExist as exc:
        raise Http404 from exc


def _last_action(game: Game) -> tuple[str, datetime | None]:
    roll_at = game.latest_roll_at
    score_at = game.latest_score_at

    if score_at is not None and (roll_at is None or score_at >= roll_at):
        return "Category\u00a0selected", score_at

    if roll_at is not None:
        return "Roll\u00a0accepted", roll_at

    return "Waiting for the\u00a0first roll", None


def _current_turn(game: Game) -> Turn | None:
    turns = [
        turn
        for participant in game.dashboard_participants
        for turn in participant.dashboard_open_turns
    ]

    return min(
        turns,
        key=lambda turn: (
            turn.game_participant.turn_order,
            turn.number,
            turn.pk,
        ),
        default=None,
    )


def _attention_reasons(game: Game, turn: Turn | None, now: datetime) -> list[str]:
    reasons: list[str] = []

    if game.participant_count > 0 and (
        game.completed_participant_count == game.participant_count
    ):
        return reasons

    disconnected = [
        participant.tournament_participant.display_name_snapshot
        for participant in game.dashboard_participants
        if participant.tournament_participant.connection_status
        == ParticipantConnectionStatus.DISCONNECTED
    ]

    reconnecting = [
        participant.tournament_participant.display_name_snapshot
        for participant in game.dashboard_participants
        if participant.tournament_participant.connection_status
        == ParticipantConnectionStatus.RECONNECTING
    ]

    if disconnected:
        reasons.append(f"Disconnected: {', '.join(disconnected)}")

    if reconnecting:
        reasons.append(f"Reconnecting: {', '.join(reconnecting)}")

    if (
        turn is not None
        and turn.action_deadline is not None
        and turn.action_deadline <= now
    ):
        reasons.append("Decision deadline\u00a0exceeded")

    return reasons


def _serialize_game(game: Game, now: datetime) -> dict[str, object]:
    turn = _current_turn(game)
    participant_count = game.participant_count

    complete = (
        participant_count > 0 and game.completed_participant_count == participant_count
    )

    waiting = complete and game.round.status == RoundStatus.ACTIVE
    last_action, last_action_at = _last_action(game)
    reasons = _attention_reasons(game, turn, now)

    if waiting:
        state = "waiting"
    elif complete:
        state = "completed"
    elif turn is not None and game.round.status == RoundStatus.ACTIVE:
        state = "playing"
    else:
        state = "pending"

    current_participant = (
        turn.game_participant.tournament_participant if turn is not None else None
    )

    latest_roll = (
        max(turn.dashboard_rolls, key=lambda roll: roll.roll_number, default=None)
        if turn is not None
        else None
    )

    return {
        "id": game.pk,
        "display_number": game.display_number,
        "label": f"Table\u00a0#{game.display_number}",
        "round": {
            "id": game.round_id,
            "number": game.round.number,
            "name": game.round.name,
        },
        "current_participant": (
            {
                "id": current_participant.pk,
                "name": current_participant.display_name_snapshot,
            }
            if current_participant is not None
            else None
        ),
        "participant_ids": [
            participant.tournament_participant_id
            for participant in game.dashboard_participants
        ],
        "turn_number": turn.number if turn is not None else None,
        "roll_number": latest_roll.roll_number if latest_roll is not None else 0,
        "last_action": last_action,
        "last_action_at": last_action_at.isoformat() if last_action_at else None,
        "state": state,
        "state_version": game.state_version,
        "requires_attention": bool(reasons),
        "attention_reasons": reasons,
    }


def get_organizer_dashboard(*, actor: User, tournament_id: int) -> dict[str, object]:
    """Return a bounded-query snapshot for every table in the current round."""
    tournament = _scoped_tournament(actor=actor, tournament_id=tournament_id)
    current_round = tournament.rounds.order_by("-number", "-pk").first()

    if current_round is None:
        games: list[Game] = []
    else:
        participant_queryset = GameParticipant.objects.select_related(
            "tournament_participant__player_profile"
        ).order_by("turn_order", "pk")

        open_turn_queryset = (
            Turn.objects.filter(completed_at__isnull=True)
            .select_related("game_participant__tournament_participant")
            .prefetch_related(Prefetch("rolls", to_attr="dashboard_rolls"))
            .order_by("game_participant__turn_order", "number", "pk")
        )

        participant_queryset = participant_queryset.prefetch_related(
            Prefetch(
                "turns", queryset=open_turn_queryset, to_attr="dashboard_open_turns"
            )
        )

        games = list(
            Game.objects.filter(round=current_round)
            .select_related("round", "round__tournament")
            .annotate(
                participant_count=Count("game_participants", distinct=True),
                completed_participant_count=Count(
                    "game_participants",
                    filter=Q(game_participants__is_completed=True),
                    distinct=True,
                ),
                latest_roll_at=Max("game_participants__turns__rolls__rolled_at"),
                latest_score_at=Max("game_participants__score_entries__created_at"),
            )
            .prefetch_related(
                Prefetch(
                    "game_participants",
                    queryset=participant_queryset,
                    to_attr="dashboard_participants",
                )
            )
            .order_by("display_number", "pk")
        )

    now = timezone.now()
    cards = [_serialize_game(game, now) for game in games]

    attention = [
        {
            "table_id": card["id"],
            "display_number": card["display_number"],
            "label": card["label"],
            "reasons": card["attention_reasons"],
        }
        for card in cards
        if card["requires_attention"]
    ]

    return {
        "tournament": {
            "id": tournament.pk,
            "name": tournament.name,
            "status": tournament.status,
        },
        "round": (
            {
                "id": current_round.pk,
                "number": current_round.number,
                "name": current_round.name,
                "status": current_round.status,
            }
            if current_round is not None
            else None
        ),
        "summary": {
            "tables": len(cards),
            "playing": sum(card["state"] == "playing" for card in cards),
            "completed": sum(
                card["state"] in {"completed", "waiting"} for card in cards
            ),
            "waiting": sum(card["state"] == "waiting" for card in cards),
            "attention": len(attention),
        },
        "tables": cards,
        "attention": attention,
    }
