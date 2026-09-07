import secrets
from collections.abc import Callable
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from accounts.models import User
from tournaments.domain.tournament.allocation import generate_group_allocation
from tournaments.domain.tournament.allocation.types import (
    AllocationEvaluation,
    AllocationParticipant,
)
from tournaments.domain.tournament.rounds import RoundStatus, RoundType
from tournaments.domain.tournament.tie_break import (
    MaterialTie,
    controlled_draw,
    top_material_tie,
)
from tournaments.domain.tournament.types import ParticipantStatus
from tournaments.models import (
    Game,
    GameParticipant,
    Round,
    TieBreakDecision,
    Tournament,
    TournamentOrganizer,
    TournamentParticipant,
)
from tournaments.services.ranking import CompletedResult, RankingRow, build_ranking

type Publisher = Callable[[str, dict[str, int]], None]


@dataclass(frozen=True, slots=True)
class BarrierResult:
    state: str
    round_id: int | None = None
    tied_participant_ids: tuple[int, ...] = ()
    selected_participant_id: int | None = None


def get_tournament_ranking(tournament_id: int) -> tuple[RankingRow, ...]:
    results = GameParticipant.objects.filter(
        game__round__tournament_id=tournament_id,
        game__round__number__lte=F("game__round__tournament__group_rounds"),
        is_completed=True,
    ).values_list("tournament_participant_id", "raw_score")

    return build_ranking(
        CompletedResult(participant_id=pk, score=score) for pk, score in results
    )


def _repeated_pairs(tournament_id: int) -> set[frozenset[int]]:
    pairs: set[frozenset[int]] = set()

    games = Game.objects.filter(round__tournament_id=tournament_id).prefetch_related(
        "game_participants"
    )

    for game in games:
        ids = [gp.tournament_participant_id for gp in game.game_participants.all()]

        for index, first in enumerate(ids):
            for second in ids[index + 1 :]:
                pairs.add(frozenset((first, second)))

    return pairs


def _create_games_from_allocation(
    *,
    round_: Round,
    participants: list[TournamentParticipant],
    evaluation: AllocationEvaluation,
    seed: int,
) -> None:
    participant_map = {participant.pk: participant for participant in participants}

    for display_number, assignment in enumerate(
        evaluation.candidate.assignments,
        start=1,
    ):
        game = Game.objects.create(
            round=round_,
            display_number=display_number,
            allocation_seed=seed,
            allocation_cost=int(evaluation.cost.weighted_total),
        )

        GameParticipant.objects.bulk_create(
            [
                GameParticipant(
                    game=game,
                    tournament_participant=participant_map[participant_id],
                    turn_order=turn_order,
                )
                for turn_order, participant_id in enumerate(assignment, start=1)
            ]
        )


def _create_allocated_round(
    *,
    current_round: Round,
    participant_ids: tuple[int, ...],
    ranking: tuple[RankingRow, ...],
    overtime: bool = False,
) -> Round:
    tournament = current_round.tournament
    next_number = current_round.number + 1

    next_round = Round.objects.create(
        tournament=tournament,
        number=next_number,
        name=(
            f"Dogrywka {next_number - tournament.group_rounds}"
            if overtime
            else f"Runda {next_number}"
        ),
        type=RoundType.OVERTIME if overtime else RoundType.GROUP,
        status=RoundStatus.WAITING,
    )

    rank_order = {row.participant_id: index for index, row in enumerate(ranking)}

    participants = list(
        tournament.tournament_participants.filter(pk__in=participant_ids).order_by("pk")
    )

    participants.sort(key=lambda participant: rank_order.get(participant.pk, 10**9))

    allocation_participants = tuple(
        AllocationParticipant(id=participant.pk, team_label=participant.team_label)
        for participant in participants
    )

    seed = secrets.randbits(63)

    evaluation = generate_group_allocation(
        participants=allocation_participants,
        preferred_size=tournament.table_size,
        repeated_pairs=_repeated_pairs(tournament.pk),
        allocation_seed=seed,
    )

    _create_games_from_allocation(
        round_=next_round,
        participants=participants,
        evaluation=evaluation,
        seed=seed,
    )

    return next_round


def _resolve_draw(
    *,
    current_round: Round,
    material_tie: MaterialTie,
    organizer: User,
    draw_reason: str,
):
    tournament = current_round.tournament

    if (
        organizer is None
        or not TournamentOrganizer.objects.filter(
            tournament=tournament,
            user=organizer,
        ).exists()
    ):
        raise PermissionDenied("Only an organizer can authorize a draw.")

    reason = draw_reason.strip()

    if not reason:
        raise ValidationError("A draw requires a reason.")

    selected_id = controlled_draw(
        material_tie.participant_ids,
        secrets.SystemRandom(),
    )

    TieBreakDecision.objects.create(
        tournament=tournament,
        round=current_round,
        organizer=organizer,
        candidate_participant_ids=list(material_tie.participant_ids),
        selected_participant_id=selected_id,
        reason=reason,
    )

    current_round.status = RoundStatus.COMPLETED
    current_round.ended_at = timezone.now()
    current_round.save(update_fields=("status", "ended_at"))

    return BarrierResult(
        state="drawn",
        round_id=current_round.pk,
        tied_participant_ids=material_tie.participant_ids,
        selected_participant_id=selected_id,
    )


def evaluate_round_barrier(
    *,
    round_id: int,
    publisher: Publisher,
    organizer: User | None = None,
    draw_reason: str = "",
    force_draw: bool = False,
):
    with transaction.atomic():
        current_round = (
            Round.objects.select_for_update()
            .select_related("tournament")
            .get(pk=round_id)
        )

        tournament = current_round.tournament

        if force_draw and current_round.number < tournament.group_rounds:
            raise ValidationError("A draw is unavailable before the final group round.")

        if (
            current_round.games.filter(
                Q(game_participants__is_completed=False)
                | Q(game_participants__isnull=True)
            ).exists()
            or not current_round.games.exists()
        ):
            return BarrierResult(state="waiting", round_id=current_round.pk)

        existing = tournament.rounds.filter(number=current_round.number + 1).first()

        if existing is not None:
            return BarrierResult(state="existing", round_id=existing.pk)

        ranking = get_tournament_ranking(tournament.pk)

        if current_round.number >= tournament.group_rounds:
            if current_round.type == RoundType.OVERTIME:
                overtime_results = current_round.games.filter(
                    game_participants__is_completed=True
                ).values_list(
                    "game_participants__tournament_participant_id",
                    "game_participants__raw_score",
                )

                decisive_ranking = build_ranking(
                    CompletedResult(participant_id=pk, score=score)
                    for pk, score in overtime_results
                )

            else:
                decisive_ranking = ranking

            material_tie = top_material_tie(decisive_ranking)

            if material_tie is not None:
                if force_draw:
                    return _resolve_draw(
                        current_round=current_round,
                        material_tie=material_tie,
                        organizer=organizer,
                        draw_reason=draw_reason,
                    )

                next_round = _create_allocated_round(
                    current_round=current_round,
                    participant_ids=material_tie.participant_ids,
                    ranking=decisive_ranking,
                    overtime=True,
                )

                current_round.status = RoundStatus.COMPLETED
                current_round.ended_at = timezone.now()
                current_round.save(update_fields=("status", "ended_at"))

                transaction.on_commit(
                    lambda: publisher("round_transition", {"round_id": next_round.pk})
                )

                return BarrierResult(
                    state="overtime_created",
                    round_id=next_round.pk,
                    tied_participant_ids=material_tie.participant_ids,
                )

            if force_draw:
                raise ValidationError("There is no material tie to draw.")

            current_round.status = RoundStatus.COMPLETED
            current_round.ended_at = timezone.now()
            current_round.save(update_fields=("status", "ended_at"))

            return BarrierResult(state="tournament_ready", round_id=current_round.pk)

        participant_ids = tuple(row.participant_id for row in ranking)

        next_round = _create_allocated_round(
            current_round=current_round,
            participant_ids=participant_ids,
            ranking=ranking,
        )

        current_round.status = RoundStatus.COMPLETED
        current_round.ended_at = timezone.now()
        current_round.save(update_fields=("status", "ended_at"))

        transaction.on_commit(
            lambda: publisher("round_transition", {"round_id": next_round.pk})
        )

        return BarrierResult(state="created", round_id=next_round.pk)


def create_initial_round(tournament: Tournament) -> Round:
    if tournament.rounds.exists():
        raise ValidationError("Tournament already has rounds.")

    participants = list(
        tournament.tournament_participants.filter(
            status=ParticipantStatus.ACTIVE
        ).order_by(
            "seeding",
            "starting_number",
            "pk",
        )
    )

    allocation_participants = tuple(
        AllocationParticipant(id=participant.pk, team_label=participant.team_label)
        for participant in participants
    )

    seed = secrets.randbits(63)

    evaluation = generate_group_allocation(
        participants=allocation_participants,
        preferred_size=tournament.table_size,
        repeated_pairs=(),
        allocation_seed=seed,
    )

    round_ = Round.objects.create(
        tournament=tournament,
        number=1,
        name="Runda 1",
        status=RoundStatus.WAITING,
    )

    _create_games_from_allocation(
        round_=round_,
        participants=participants,
        evaluation=evaluation,
        seed=seed,
    )

    return round_
