from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from random import Random, SystemRandom
from unittest.mock import patch

from django.db import transaction
from django.db.models import QuerySet
from faker import Faker

from accounts.factories import PlayerProfileFactory, UserFactory
from accounts.models import PlayerProfile, User
from tournaments.domain.dice.categories import ScoreCategory
from tournaments.domain.tournament.types import (
    EventMode,
    ParticipantConnectionStatus,
    PokerScoringVariant,
    RegistrationMode,
    TournamentStatus,
)
from tournaments.models import Game, Round, TieBreakDecision, Tournament, Turn
from tournaments.services.dice.hold_dice import set_held_dice
from tournaments.services.dice.roll_dice import execute_roll
from tournaments.services.dice.select_category import select_category
from tournaments.services.participants import create_participant
from tournaments.services.round_barrier import evaluate_round_barrier
from tournaments.services.tournament_lifecycle import (
    complete_tournament,
    create_tournament,
    open_registration,
    start_tournament,
)

SUPPORTED_DEMO_SIZES = frozenset({16, 64, 128})
SUPPORTED_DEMO_SCENARIOS = frozenset(
    {
        "fresh",
        "active-round",
        "mixed-table-states",
        "completed",
        "conflicts",
        "reconnect",
    }
)


@dataclass(frozen=True, slots=True)
class DemoWorld:
    namespace: str
    organizer_username: str
    tournament_id: int
    participant_count: int
    table_count: int


class _FixedDiceRandomizer:
    def __init__(self, values: tuple[int, int, int, int, int]):
        self._values = iter(values)

    def randint(self, _minimum: int, _maximum: int) -> int:
        return next(self._values)


class DemoWorldBuilder:
    """Build demo worlds with seed-reproducible content through domain services."""

    def __init__(
        self,
        *,
        size: int,
        scenario: str,
        seed: int,
        password: str,
    ) -> None:
        if size not in SUPPORTED_DEMO_SIZES:
            raise ValueError("Demo size must be one of: 16, 64, 128.")

        if scenario not in SUPPORTED_DEMO_SCENARIOS:
            raise ValueError(f"Unsupported demo scenario: {scenario}.")

        self.size = size
        self.scenario = scenario

        self.seed = seed
        self.password = password

        self.namespace = f"demo:{scenario}:{seed}:{size}"
        self.slug = f"demo-{scenario}-{seed}-{size}"

        self.rng = Random(seed)
        self.faker = Faker("pl_PL")
        self.faker.seed_instance(seed)

    @transaction.atomic
    def build(self):
        if self._namespace_tournaments().exists():
            raise ValueError(
                "Demo namespace already exists. Re-run seed_demo with --reset."
            )

        organizer = self._create_organizer()
        profiles = self._create_player_profiles()

        tournament_count = (
            SystemRandom().randint(2, 4) if self.scenario == "completed" else 1
        )

        tournaments = [
            self._build_tournament(
                organizer=organizer,
                profiles=profiles,
                sequence=sequence,
            )
            for sequence in range(1, tournament_count + 1)
        ]

        tournament = tournaments[0]

        return DemoWorld(
            namespace=self.namespace,
            organizer_username=organizer.username,
            tournament_id=tournament.pk,
            participant_count=tournament.tournament_participants.count(),
            table_count=self._dashboard_table_count(tournament),
        )

    def _namespace_tournaments(self) -> QuerySet[Tournament]:
        return Tournament.objects.filter(
            name__startswith=self._tournament_name,
            organizers__username=f"{self.slug}-organizer",
        ).distinct()

    def _build_tournament(
        self,
        *,
        organizer: User,
        profiles: tuple[PlayerProfile, ...],
        sequence: int,
    ) -> Tournament:
        name = (
            self._tournament_name
            if sequence == 1
            else f"{self._tournament_name} | #{sequence}"
        )

        tournament = create_tournament(
            organizer=organizer,
            name=name,
            status=TournamentStatus.DRAFT,
            registration_mode=RegistrationMode.ORGANIZER_ONLY,
            min_participants=2,
            max_participants=self.size,
            timezone="Europe/Warsaw",
            group_rounds=2,
            table_size=4,
            poker_scoring_variant=PokerScoringVariant.A,
            event_mode=EventMode.REMOTE,
        )

        open_registration(tournament)
        self._create_participants(tournament=tournament, profiles=profiles)

        if self.scenario != "fresh":
            deterministic_allocation_seed = self.rng.getrandbits(63)

            with patch(
                "tournaments.services.round_barrier.secrets.randbits",
                return_value=deterministic_allocation_seed,
            ):
                tournament = start_tournament(tournament)

            self._shape_active_state(tournament)

        tournament.refresh_from_db()
        return tournament

    @staticmethod
    def _dashboard_table_count(tournament: Tournament) -> int:
        latest_round = tournament.rounds.order_by("-number").first()
        return latest_round.games.count() if latest_round is not None else 0

    @property
    def _tournament_name(self) -> str:
        return f"Demo Tournament | {self.scenario} | {self.seed} | {self.size}"

    def _create_organizer(self) -> User:
        return UserFactory.create(
            username=f"{self.slug}-organizer",
            email=f"organizer@{self.slug}.test",
            first_name="Marta",
            last_name="Nowak",
            password=self.password,
        )

    def _create_player_profiles(self) -> tuple[PlayerProfile, ...]:
        profiles = []

        for number in range(1, self.size + 1):
            first_name = self.faker.first_name()
            last_name = self.faker.last_name()
            username = f"{self.slug}-p{number:03d}"
            nickname = f"player{number:03d}"

            profiles.append(
                PlayerProfileFactory.create(
                    user__username=username,
                    user__email=f"{username}@arena.test",
                    user__first_name=first_name,
                    user__last_name=last_name,
                    user__password=self.password,
                    display_name=f"{first_name} {last_name}",
                    nickname=nickname,
                )
            )

        return tuple(profiles)

    def _create_participants(
        self,
        *,
        tournament: Tournament,
        profiles: tuple[PlayerProfile, ...],
    ) -> None:
        team_labels = ("North", "South", "East", "West")

        for number, profile in enumerate(profiles, start=1):
            if self.scenario == "conflicts":
                team_label = "Team Alpha" if number % 2 else "Team Beta"
            else:
                team_label = team_labels[(number - 1) % len(team_labels)]

            create_participant(
                tournament=tournament,
                player_profile=profile,
                team_label=team_label,
                starting_number=number,
                seeding=number,
            )

    def _shape_active_state(self, tournament: Tournament) -> None:
        round_ = tournament.rounds.get(number=1)
        games = list(round_.games.order_by("display_number"))

        if self.scenario == "mixed-table-states" and games:
            self._finish_round(round_)

            with patch(
                "tournaments.services.round_barrier.secrets.randbits",
                return_value=self.rng.getrandbits(63),
            ):
                result = evaluate_round_barrier(
                    round_id=round_.pk,
                    publisher=lambda _event, _payload: None,
                )

            active_round = tournament.rounds.get(pk=result.round_id)
            games = list(active_round.games.order_by("display_number"))
            waiting_limit = max(1, len(games) // 3)
            waiting_count = self.rng.randint(1, waiting_limit)
            waiting_games = self.rng.sample(games, k=waiting_count)

            for game in waiting_games:
                game.game_participants.update(
                    is_completed=True,
                    raw_score=120 + game.display_number,
                    final_score=120 + game.display_number,
                )

                Turn.objects.filter(
                    game_participant__game=game,
                    completed_at__isnull=True,
                    rolls__isnull=True,
                ).delete()

                game.state_version = 1
                game.save(update_fields=("state_version",))

            playing_games = [game for game in games if game not in waiting_games]

            for game in playing_games[: min(3, len(playing_games))]:
                self._roll_once(game)

        if self.scenario == "reconnect":
            participants = tournament.tournament_participants.order_by(
                "starting_number"
            )

            first = participants.first()
            second = participants[1] if participants.count() > 1 else None

            if first is not None:
                first.connection_status = ParticipantConnectionStatus.RECONNECTING
                first.save(update_fields=("connection_status",))

            if second is not None:
                second.connection_status = ParticipantConnectionStatus.DISCONNECTED
                second.save(update_fields=("connection_status",))

        if self.scenario == "completed":
            self._build_complete_history(round_)
            self._finish_round(round_)

            with patch(
                "tournaments.services.round_barrier.secrets.randbits",
                return_value=self.rng.getrandbits(63),
            ):
                result = evaluate_round_barrier(
                    round_id=round_.pk,
                    publisher=lambda _event, _payload: None,
                )

            second_round = tournament.rounds.get(pk=result.round_id)
            self._build_complete_history(second_round)
            self._finish_round(second_round)

            evaluate_round_barrier(
                round_id=second_round.pk,
                publisher=lambda _event, _payload: None,
            )

            complete_tournament(tournament)

    def _roll_once(self, game: Game) -> None:
        game_participant = (
            game.game_participants.filter(turns__completed_at__isnull=True)
            .select_related("tournament_participant__player_profile__user")
            .order_by("turn_order", "turns__number", "turns__pk")
            .first()
        )

        if game_participant is None:
            return

        user = game_participant.tournament_participant.player_profile.user

        execute_roll(
            user=user,
            game_id=game.pk,
            payload={},
            key=f"{self.slug}-game-{game.pk}-sample-roll",
            rng=self.rng,
            publisher=lambda _event, _payload: None,
        )

    def _build_complete_history(self, round_: Round) -> None:
        categories = tuple(ScoreCategory)

        for game in round_.games.order_by("display_number"):
            participants_this_cycle = game.game_participants.count()

            for category in categories:
                for _ in range(participants_this_cycle):
                    game_participant = (
                        game.game_participants.filter(turns__completed_at__isnull=True)
                        .select_related("tournament_participant__player_profile__user")
                        .order_by("turn_order", "turns__number", "turns__pk")
                        .first()
                    )

                    if game_participant is None:
                        return

                    current_turn = (
                        game_participant.turns.filter(completed_at__isnull=True)
                        .order_by("number", "pk")
                        .first()
                    )

                    if current_turn is None:
                        return

                    user = game_participant.tournament_participant.player_profile.user

                    starting_number = (
                        game_participant.tournament_participant.starting_number
                    )

                    roll_count, fixed_values = self._demo_turn_plan(
                        category=category,
                        starting_number=starting_number,
                    )

                    for roll_index in range(roll_count):
                        roll_rng = (
                            _FixedDiceRandomizer(fixed_values)
                            if fixed_values is not None
                            else self.rng
                        )

                        execute_roll(
                            user=user,
                            game_id=game.pk,
                            payload={},
                            key=(
                                f"{self.slug}-g{game.pk}-p{game_participant.pk}-"
                                f"t{current_turn.number}-r{roll_index + 1}"
                            ),
                            rng=roll_rng,
                            publisher=lambda _event, _payload: None,
                        )

                        if roll_index < roll_count - 1:
                            self._set_demo_holds(
                                user=user,
                                game=game,
                                turn=current_turn,
                            )

                    payload = {"category": category.value}
                    last_roll = current_turn.rolls.order_by("roll_number").last()

                    if category is ScoreCategory.PAIR and last_roll is not None:
                        counts = Counter(last_roll.values)

                        eligible = [
                            value for value, count in counts.items() if count >= 2
                        ]

                        if eligible:
                            payload["pair_value"] = max(eligible)

                    select_category(
                        user=user,
                        game_id=game.pk,
                        payload=payload,
                        key=(
                            f"{self.slug}-g{game.pk}-p{game_participant.pk}-"
                            f"t{current_turn.number}-category"
                        ),
                        publisher=lambda _event, _payload: None,
                    )

            Turn.objects.filter(
                game_participant__game=game,
                completed_at__isnull=True,
                rolls__isnull=True,
            ).delete()

    def _demo_turn_plan(
        self,
        *,
        category: ScoreCategory,
        starting_number: int,
    ) -> tuple[int, tuple[int, int, int, int, int] | None]:
        controlled_rolls = {
            (1, ScoreCategory.ONES): (1, 1, 1, 1, 2),
            (2, ScoreCategory.TWOS): (2, 2, 2, 1, 3),
            (3, ScoreCategory.THREES): (3, 3, 1, 2, 4),
            (4, ScoreCategory.PAIR): (6, 6, 1, 2, 3),
            (6, ScoreCategory.POKER): (1, 2, 3, 4, 5),
        }

        fixed_values = controlled_rolls.get((starting_number, category))

        if fixed_values is not None:
            return 1, fixed_values

        if starting_number == 5 and category is ScoreCategory.CHANCE:
            return 2, None

        return self.rng.randint(1, 3), None

    def _set_demo_holds(
        self,
        *,
        user: User,
        game: Game,
        turn: Turn,
    ) -> None:
        turn.refresh_from_db()
        current_flags = turn.held_dice
        held_count = self.rng.randint(0, 4)

        held_positions = set(self.rng.sample(range(5), k=held_count))
        held_flags = tuple(position in held_positions for position in range(5))

        if held_flags == current_flags:
            held_flags_list = list(held_flags)

            position = (
                held_flags_list.index(True)
                if held_count == 4
                else held_flags_list.index(False)
            )

            held_flags_list[position] = not held_flags_list[position]
            held_flags = tuple(held_flags_list)

        set_held_dice(
            user=user,
            game_id=game.pk,
            held_flags=held_flags,
            publisher=lambda _event, _payload: None,
        )

    def _finish_round(self, round_: Round) -> None:
        for game in round_.games.order_by("display_number"):
            for participant in game.game_participants.order_by("turn_order"):
                participant.is_completed = True

                if not participant.score_entries.exists():
                    score = (
                        self.size
                        + 1
                        - participant.tournament_participant.starting_number
                    )
                    participant.raw_score = score
                    participant.final_score = score
                    update_fields = ("is_completed", "raw_score", "final_score")
                else:
                    # Preserve aggregates produced from the real score entries
                    # used by the representative replay instead of replacing them
                    # with the lightweight completion score used for untouched players.
                    update_fields = ("is_completed",)

                participant.save(update_fields=update_fields)

            Turn.objects.filter(
                game_participant__game=game,
                completed_at__isnull=True,
                rolls__isnull=True,
            ).delete()

            game.state_version = max(1, game.state_version + 1)
            game.save(update_fields=("state_version",))


def delete_demo_namespace(*, scenario: str, seed: int, size: int) -> None:
    slug = f"demo-{scenario}-{seed}-{size}"
    tournament_name = f"Demo Tournament | {scenario} | {seed} | {size}"

    with transaction.atomic():
        tournaments = Tournament.objects.filter(
            name__startswith=tournament_name,
            organizers__username=f"{slug}-organizer",
        ).distinct()

        if not tournaments.exists():
            return

        user_ids = set(
            tournaments.values_list("tournament_organizers__user_id", flat=True)
        )

        user_ids.update(
            tournaments.values_list(
                "tournament_participants__player_profile__user_id",
                flat=True,
            )
        )

        # Remove objects whose protected foreign keys would otherwise block
        # deletion of the tournament's participants or rounds.
        TieBreakDecision.objects.filter(tournament__in=tournaments).delete()

        Game.objects.filter(
            round__tournament__in=tournaments,
        ).delete()

        tournaments.delete()

        User.objects.filter(
            pk__in=user_ids,
            username__startswith=f"{slug}-",
        ).delete()
