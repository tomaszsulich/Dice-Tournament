from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404

from accounts.models import PlayerProfile, User
from tournaments.domain.dice.categories import SCHOOL_CATEGORIES, ScoreCategory
from tournaments.models import (
    GameParticipant,
    Roll,
    ScoreResultKind,
    Tournament,
    TournamentParticipant,
)

COMPARABLE_TOURNAMENT_STATUSES = ("completed", "archived")
MIN_COMPARISON_TOURNAMENTS = 1
MAX_COMPARISON_TOURNAMENTS = 4
HISTORY_PAGE_SIZE = 20


class InvalidComparison(ValueError):
    """Report malformed comparison input without disclosing scoped objects."""


@dataclass(frozen=True, slots=True)
class ComparisonSelection:
    tournament_ids: tuple[int, ...]

    @classmethod
    def parse(cls, raw_ids: Iterable[object]) -> "ComparisonSelection":
        try:
            ids = tuple(int(raw_id) for raw_id in raw_ids)
        except (TypeError, ValueError) as exc:
            raise InvalidComparison("Tournament IDs must be integers.") from exc

        if len(ids) != len(set(ids)):
            raise InvalidComparison("Tournament IDs must be unique.")

        if not MIN_COMPARISON_TOURNAMENTS <= len(ids) <= MAX_COMPARISON_TOURNAMENTS:
            raise InvalidComparison("Select between one and four tournaments.")

        if any(tournament_id <= 0 for tournament_id in ids):
            raise InvalidComparison("Tournament IDs must be positive integers.")

        return cls(tournament_ids=ids)


def _actor_scope(actor: User) -> Q:
    return Q() if actor.is_superuser else Q(organizers=actor)


def get_comparison_options(*, actor: User, participant_id: int) -> dict[str, object]:
    try:
        profile = PlayerProfile.objects.get(pk=participant_id)
    except PlayerProfile.DoesNotExist as exc:
        raise Http404 from exc

    tournaments = list(
        Tournament.objects.filter(
            _actor_scope(actor),
            status__in=COMPARABLE_TOURNAMENT_STATUSES,
            tournament_participants__player_profile=profile,
        )
        .distinct()
        .order_by("-completed_at", "-pk")
        .values("id", "name", "status", "completed_at")
    )

    if not tournaments:
        raise Http404

    return {
        "participant": {"id": profile.pk, "name": str(profile)},
        "tournaments": tournaments,
    }


def get_own_history_options(*, actor: User) -> dict[str, object]:
    """Return completed tournaments whose roll history belongs to the actor."""
    try:
        profile = PlayerProfile.objects.get(user=actor)
    except PlayerProfile.DoesNotExist as exc:
        raise Http404 from exc

    participations = list(
        TournamentParticipant.objects.filter(
            player_profile=profile,
            tournament__status__in=COMPARABLE_TOURNAMENT_STATUSES,
        )
        .select_related("tournament")
        .prefetch_related("tournament__rounds")
        .order_by("-tournament__completed_at", "-tournament_id")
    )

    return {
        "participant": {"id": profile.pk, "name": str(profile)},
        "tournaments": [
            {
                "tournament": {
                    "id": participation.tournament_id,
                    "name": participation.tournament.name,
                    "timezone": participation.tournament.timezone,
                },
                "rounds": [
                    {
                        "round_id": round_.pk,
                        "round_number": round_.number,
                        "round_name": round_.name,
                    }
                    for round_ in sorted(
                        participation.tournament.rounds.all(),
                        key=lambda item: (item.number, item.pk),
                    )
                ],
            }
            for participation in participations
        ],
    }


def compare_participant(
    *, actor: User, participant_id: int, tournament_ids: Iterable[object]
) -> dict[str, object]:
    """Aggregate accepted round results after one all-or-nothing access check."""
    selection = ComparisonSelection.parse(tournament_ids)

    tournaments = list(
        Tournament.objects.filter(
            _actor_scope(actor),
            pk__in=selection.tournament_ids,
            status__in=COMPARABLE_TOURNAMENT_STATUSES,
        )
        .distinct()
        .order_by("pk")
    )

    if {item.pk for item in tournaments} != set(selection.tournament_ids):
        raise Http404

    participations = list(
        TournamentParticipant.objects.filter(
            tournament_id__in=selection.tournament_ids,
            player_profile_id=participant_id,
        )
        .select_related("player_profile")
        .order_by("tournament_id")
    )

    participation_by_tournament = {
        participation.tournament_id: participation for participation in participations
    }

    if set(participation_by_tournament) != set(selection.tournament_ids):
        raise Http404

    results = list(
        GameParticipant.objects.filter(
            tournament_participant__player_profile_id=participant_id,
            game__round__tournament_id__in=selection.tournament_ids,
            is_completed=True,
        )
        .select_related("game__round", "tournament_participant")
        .order_by("game__round__tournament_id", "game__round__number", "pk")
    )

    results_by_tournament: dict[int, list[GameParticipant]] = {
        tournament_id: [] for tournament_id in selection.tournament_ids
    }

    for result in results:
        results_by_tournament[result.game.round.tournament_id].append(result)

    tournament_by_id = {tournament.pk: tournament for tournament in tournaments}
    comparisons = []

    for tournament_id in selection.tournament_ids:
        tournament = tournament_by_id[tournament_id]
        participation = participation_by_tournament[tournament_id]

        round_results = results_by_tournament[tournament_id]
        scores = [result.raw_score for result in round_results]

        rounds_played = len(scores)
        total = sum(scores)

        average = (
            Decimal(total) / Decimal(rounds_played) if rounds_played else Decimal("0")
        )

        comparisons.append(
            {
                "tournament": {
                    "id": tournament.pk,
                    "name": tournament.name,
                    "status": tournament.status,
                    "timezone": tournament.timezone,
                    "completed_at": (
                        tournament.completed_at.isoformat()
                        if tournament.completed_at is not None
                        else None
                    ),
                },
                "participant_snapshot": {
                    "full_name": participation.full_name_snapshot,
                    "display_name": participation.display_name_snapshot,
                    "nickname": participation.nickname_snapshot,
                    "starting_number": participation.starting_number,
                    "seeding": participation.seeding,
                },
                "total": total,
                "round_average": float(average.quantize(Decimal("0.01"))),
                "best_round": max(scores) if scores else None,
                "rounds_played": rounds_played,
                "rounds": [
                    {
                        "round_id": result.game.round_id,
                        "round_number": result.game.round.number,
                        "round_name": result.game.round.name,
                        "game_id": result.game_id,
                        "table_number": result.game.display_number,
                        "score": result.raw_score,
                    }
                    for result in round_results
                ],
            }
        )

    profile = participations[0].player_profile

    return {
        "participant": {"id": profile.pk, "name": str(profile)},
        "comparisons": comparisons,
    }


def _serialize_history_roll(roll: Roll) -> dict[str, object]:
    turn_rolls = sorted(
        roll.turn.rolls.all(),
        key=lambda item: (item.roll_number, item.pk),
    )

    current_index = next(
        index for index, item in enumerate(turn_rolls) if item.pk == roll.pk
    )

    next_roll = (
        turn_rolls[current_index + 1] if current_index + 1 < len(turn_rolls) else None
    )

    decision = None

    if current_index == len(turn_rolls) - 1 and hasattr(roll.turn, "score_entry"):
        entry = roll.turn.score_entry
        category = ScoreCategory(entry.category)

        decision = {
            "category": entry.category,
            "category_label": category.label,
            "result_kind": entry.result_kind,
            "result_label": entry.get_result_kind_display(),
            "value": entry.value,
            "selected_at": entry.created_at.isoformat(),
            "first_roll_bonus_applied": (
                roll.roll_number == 1
                and category not in SCHOOL_CATEGORIES
                and entry.result_kind == ScoreResultKind.POINTS
            ),
        }

    return {
        "id": roll.pk,
        "round_id": roll.turn.game_participant.game.round_id,
        "round_number": roll.turn.game_participant.game.round.number,
        "table_number": roll.turn.game_participant.game.display_number,
        "turn_number": roll.turn.number,
        "roll_number": roll.roll_number,
        "dice": list(roll.values),
        # Kept for API compatibility: this is the hold state used for this roll.
        "held": list(roll.held_after_roll),
        "held_for_roll": list(roll.held_after_roll),
        # Holds chosen after this roll are persisted on the next roll snapshot.
        "held_after_roll": (
            list(next_roll.held_after_roll) if next_roll is not None else None
        ),
        "rolled_at": roll.rolled_at.isoformat(),
        "decision": decision,
    }


def get_participant_history_page(
    *,
    actor: User,
    participant_id: int,
    tournament_id: int,
    page_number: object,
    round_id: int | None = None,
) -> dict[str, object]:
    participation = (
        TournamentParticipant.objects.filter(
            tournament_id=tournament_id,
            tournament__status__in=COMPARABLE_TOURNAMENT_STATUSES,
            player_profile_id=participant_id,
        )
        .select_related("player_profile__user", "tournament")
        .first()
    )

    if participation is None:
        raise Http404

    is_owner = participation.player_profile.user_id == actor.pk
    is_organizer = participation.tournament.organizers.filter(pk=actor.pk).exists()

    if not actor.is_superuser and not is_owner and not is_organizer:
        raise Http404

    history_scope = {
        "turn__game_participant__tournament_participant__player_profile_id": (
            participant_id
        ),
        "turn__game_participant__game__round__tournament_id": tournament_id,
        "turn__game_participant__is_completed": True,
    }

    if round_id is not None:
        history_scope["turn__game_participant__game__round_id"] = round_id

    rolls = (
        Roll.objects.filter(**history_scope)
        .select_related(
            "turn__game_participant__game__round",
            "turn__score_entry",
        )
        .prefetch_related("turn__rolls")
        .order_by(
            "turn__game_participant__game__round__number",
            "turn__game_participant__game__display_number",
            "turn__number",
            "roll_number",
            "pk",
        )
    )

    paginator = Paginator(rolls, HISTORY_PAGE_SIZE)

    try:
        page = paginator.get_page(page_number)
    except (TypeError, ValueError):
        page = paginator.get_page(1)

    return {
        "items": [_serialize_history_roll(roll) for roll in page.object_list],
        "pagination": {
            "page": page.number,
            "pages": paginator.num_pages,
            "count": paginator.count,
            "has_next": page.has_next(),
        },
    }
