import re
from collections import Counter, defaultdict
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.db.models import Count
from django.test import override_settings

from accounts.models import User
from tournaments.demo_builders import DemoWorldBuilder
from tournaments.domain.dice.categories import SCHOOL_CATEGORIES, ScoreCategory
from tournaments.domain.tournament.types import TournamentStatus
from tournaments.models import Game, Roll, ScoreEntry, ScoreResultKind, Tournament, Turn
from tournaments.selectors.organizer_dashboard import get_organizer_dashboard
from tournaments.selectors.participant_comparison import (
    get_comparison_options,
    get_participant_history_page,
)

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


def _mixed_state_signature(tournament: Tournament) -> tuple[tuple[int, ...], tuple]:
    round_ = tournament.rounds.get(number=2)

    waiting_tables = tuple(
        game.display_number
        for game in round_.games.order_by("display_number")
        if not game.game_participants.filter(is_completed=False).exists()
    )

    roll_snapshots = tuple(
        (
            roll.turn.game_participant.game.display_number,
            roll.turn.game_participant.tournament_participant.starting_number,
            roll.values,
        )
        for roll in Roll.objects.filter(turn__game_participant__game__round=round_)
        .select_related(
            "turn__game_participant__game",
            "turn__game_participant__tournament_participant",
        )
        .order_by("turn__game_participant__game__display_number", "pk")
    )

    return waiting_tables, roll_snapshots


def _logical_assignment(tournament: Tournament) -> tuple[tuple[int, ...], ...]:
    round_ = tournament.rounds.get(number=1)
    return tuple(
        tuple(
            game.game_participants.order_by("turn_order").values_list(
                "tournament_participant__starting_number",
                flat=True,
            )
        )
        for game in round_.games.order_by("display_number")
    )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@pytest.mark.parametrize(
    "size",
    [
        16,
        pytest.param(64, marks=pytest.mark.slow),
        pytest.param(128, marks=pytest.mark.slow),
    ],
)
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=True,
    PASSWORD_HASHERS=FAST_HASHERS,
)
def test_seed_demo_builds_supported_sizes_with_legal_tables(size, capsys):
    call_command(
        "seed_demo",
        size=size,
        scenario="active-round",
        seed=20260831,
    )

    tournament = Tournament.objects.get(
        name=f"Demo Tournament | active-round | 20260831 | {size}"
    )

    table_sizes = [
        game.game_participants.count()
        for game in tournament.rounds.get(number=1).games.order_by("display_number")
    ]

    assert tournament.tournament_participants.count() == size
    assert sum(table_sizes) == size
    assert all(2 <= table_size <= 6 for table_size in table_sizes)
    assert tournament.status == TournamentStatus.ACTIVE

    output = capsys.readouterr().out

    assert f"tournament_id={tournament.pk}" in output
    assert f"participants={size}" in output
    assert "demo_password=" in output


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=True,
    PASSWORD_HASHERS=FAST_HASHERS,
)
def test_seed_demo_uses_safe_realistic_local_identities():
    call_command(
        "seed_demo",
        size=16,
        scenario="fresh",
        seed=7,
        reset=True,
    )

    users = User.objects.filter(username__startswith="demo-fresh-7-16-")
    emails = list(users.values_list("email", flat=True))

    assert users.count() == 17
    assert all(email.endswith(".test") for email in emails)
    assert all("example.com" not in email for email in emails)
    assert all(re.fullmatch(r"[^@]+@[^@]+\.test", email) for email in emails)


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=True,
    PASSWORD_HASHERS=FAST_HASHERS,
)
def test_seed_demo_reset_is_scoped_and_logically_reproducible():
    unrelated = Tournament.objects.create(
        name="Developer Scratch Tournament",
        status="draft",
        registration_mode="organizer_only",
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=4,
        poker_scoring_variant="a",
        event_mode="remote",
    )

    kwargs = {
        "size": 16,
        "scenario": "active-round",
        "seed": 20260831,
    }

    call_command("seed_demo", **kwargs)

    first = Tournament.objects.get(
        name="Demo Tournament | active-round | 20260831 | 16"
    )

    first_pk = first.pk
    first_assignment = _logical_assignment(first)

    first_labels = tuple(
        first.tournament_participants.order_by("starting_number").values_list(
            "display_name_snapshot",
            flat=True,
        )
    )

    assert first.rounds.get(number=1).games.exists()

    assert Game.objects.filter(
        round__tournament=first,
        game_participants__isnull=False,
    ).exists()

    call_command("seed_demo", reset=True, **kwargs)

    second = Tournament.objects.get(
        name="Demo Tournament | active-round | 20260831 | 16"
    )

    assert _logical_assignment(second) == first_assignment

    assert (
        tuple(
            second.tournament_participants.order_by("starting_number").values_list(
                "display_name_snapshot",
                flat=True,
            )
        )
        == first_labels
    )

    assert second.pk > first_pk
    assert not Tournament.objects.filter(pk=first.pk).exists()
    assert Tournament.objects.filter(pk=unrelated.pk).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=True,
    PASSWORD_HASHERS=FAST_HASHERS,
)
def test_completed_seed_reset_replaces_every_namespace_tournament():
    unrelated = Tournament.objects.create(
        name="Developer Scratch Tournament",
        status="draft",
        registration_mode="organizer_only",
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=4,
        poker_scoring_variant="a",
        event_mode="remote",
    )

    kwargs = {
        "size": 16,
        "scenario": "completed",
        "seed": 20260831,
    }

    with (
        patch("tournaments.demo_builders.worlds.SystemRandom") as system_random,
        patch.object(DemoWorldBuilder, "_build_complete_history"),
    ):
        system_random.return_value.randint.side_effect = [3, 2]
        call_command("seed_demo", **kwargs)

        namespace = "Demo Tournament | completed | 20260831 | 16"

        first_ids = set(
            Tournament.objects.filter(name__startswith=namespace).values_list(
                "pk", flat=True
            )
        )

        assert len(first_ids) == 3

        assert (
            User.objects.filter(
                username__startswith="demo-completed-20260831-16-"
            ).count()
            == 17
        )

        call_command("seed_demo", reset=True, **kwargs)

    replacements = Tournament.objects.filter(name__startswith=namespace)
    replacement = replacements.get(name=namespace)

    assert not Tournament.objects.filter(pk__in=first_ids).exists()
    assert replacements.count() == 2
    assert replacement.pk not in first_ids
    assert Tournament.objects.filter(pk=unrelated.pk).exists()

    assert (
        User.objects.filter(username__startswith="demo-completed-20260831-16-").count()
        == 17
    )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=True,
    PASSWORD_HASHERS=FAST_HASHERS,
)
def test_mixed_table_states_use_seeded_randomness_reproducibly():
    kwargs = {
        "size": 16,
        "scenario": "mixed-table-states",
        "seed": 20260831,
    }

    call_command("seed_demo", **kwargs)

    first = Tournament.objects.get(
        name="Demo Tournament | mixed-table-states | 20260831 | 16"
    )

    first_signature = _mixed_state_signature(first)
    call_command("seed_demo", reset=True, **kwargs)

    second = Tournament.objects.get(
        name="Demo Tournament | mixed-table-states | 20260831 | 16"
    )

    second_signature = _mixed_state_signature(second)
    waiting_tables, roll_snapshots = second_signature

    assert first_signature == second_signature
    assert 0 < len(waiting_tables) < second.rounds.get(number=2).games.count()
    assert roll_snapshots

    assert not Turn.objects.filter(
        game_participant__game__round=second.rounds.get(number=2),
        game_participant__game__display_number__in=waiting_tables,
        completed_at__isnull=True,
    ).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=True,
    PASSWORD_HASHERS=FAST_HASHERS,
)
def test_seed_demo_reset_database_clears_app_data_and_restarts_identities():
    User.objects.create_user(
        username="developer-scratch-user",
        email="scratch@local.test",
        password="scratch-password",
    )

    first_scratch = Tournament.objects.create(
        name="Developer Scratch Tournament 1",
        status="draft",
        registration_mode="organizer_only",
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=4,
        poker_scoring_variant="a",
        event_mode="remote",
    )

    second_scratch = Tournament.objects.create(
        name="Developer Scratch Tournament 2",
        status="draft",
        registration_mode="organizer_only",
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=4,
        poker_scoring_variant="a",
        event_mode="remote",
    )

    assert second_scratch.pk > first_scratch.pk

    call_command(
        "seed_demo",
        size=16,
        scenario="fresh",
        seed=20260831,
        reset_database=True,
    )

    tournament = Tournament.objects.get(name="Demo Tournament | fresh | 20260831 | 16")

    organizer = User.objects.get(username="demo-fresh-20260831-16-organizer")

    assert not Tournament.objects.filter(
        name__startswith="Developer Scratch Tournament"
    ).exists()

    assert not User.objects.filter(username="developer-scratch-user").exists()
    assert tournament.pk == 1
    assert organizer.pk == 1


@pytest.mark.postgres
@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=False,
)
def test_seed_demo_reset_database_is_blocked_before_deleting_data():
    scratch = Tournament.objects.create(
        name="Protected Scratch Tournament",
        status="draft",
        registration_mode="organizer_only",
        min_participants=2,
        max_participants=16,
        timezone="Europe/Warsaw",
        group_rounds=2,
        table_size=4,
        poker_scoring_variant="a",
        event_mode="remote",
    )

    with pytest.raises(CommandError, match="forbidden when DEBUG is false"):
        call_command(
            "seed_demo",
            size=16,
            scenario="fresh",
            seed=1,
            reset_database=True,
        )

    assert Tournament.objects.filter(pk=scratch.pk).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@pytest.mark.parametrize("size", [1, 7, 129])
@override_settings(ALLOW_DEMO_SEED=True, DEBUG=True)
def test_seed_demo_rejects_unsupported_sizes(size):
    with pytest.raises(CommandError, match="--size must be one of"):
        call_command(
            "seed_demo",
            size=size,
            scenario="fresh",
            seed=1,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(ALLOW_DEMO_SEED=True, DEBUG=False)
def test_seed_demo_is_forbidden_when_debug_is_false():
    with pytest.raises(CommandError, match="forbidden when DEBUG is false"):
        call_command(
            "seed_demo",
            size=16,
            scenario="fresh",
            seed=1,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@override_settings(ALLOW_DEMO_SEED=False, DEBUG=True)
def test_seed_demo_requires_explicit_opt_in():
    with pytest.raises(CommandError, match="Demo seeding is disabled"):
        call_command(
            "seed_demo",
            size=16,
            scenario="fresh",
            seed=1,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
@pytest.mark.parametrize(
    "scenario",
    [
        "fresh",
        "active-round",
        "mixed-table-states",
        pytest.param("completed", marks=pytest.mark.slow),
        "conflicts",
        "reconnect",
    ],
)
@override_settings(
    ALLOW_DEMO_SEED=True,
    DEBUG=True,
    PASSWORD_HASHERS=FAST_HASHERS,
)
def test_seed_demo_supports_each_mvp_scenario(scenario):
    with patch("tournaments.demo_builders.worlds.SystemRandom") as system_random:
        system_random.return_value.randint.return_value = 3

        call_command(
            "seed_demo",
            size=16,
            scenario=scenario,
            seed=99,
        )

    tournament = Tournament.objects.get(name=f"Demo Tournament | {scenario} | 99 | 16")

    assert tournament.tournament_participants.count() == 16

    if scenario == "fresh":
        assert tournament.status == TournamentStatus.REGISTRATION
        assert tournament.rounds.count() == 0

    elif scenario == "completed":
        system_random.return_value.randint.assert_called_once_with(2, 4)

        completed_tournaments = list(
            Tournament.objects.filter(
                name__startswith="Demo Tournament | completed | 99 | 16"
            ).order_by("pk")
        )

        assert len(completed_tournaments) == 3

        assert [item.name for item in completed_tournaments] == [
            "Demo Tournament | completed | 99 | 16",
            "Demo Tournament | completed | 99 | 16 | #2",
            "Demo Tournament | completed | 99 | 16 | #3",
        ]

        profile_ids = set()

        for completed_tournament in completed_tournaments:
            assert completed_tournament.status == TournamentStatus.COMPLETED
            assert completed_tournament.rounds.count() == 2
            assert completed_tournament.rounds.get(number=2).games.count() == 4

            participations = list(
                completed_tournament.tournament_participants.order_by("starting_number")
            )

            assert len(participations) == 16

            profile_ids.update(
                participation.player_profile_id for participation in participations
            )

            roll_rows = list(
                Roll.objects.filter(
                    turn__game_participant__game__round__tournament=(
                        completed_tournament
                    )
                ).select_related(
                    "turn__game_participant__game__round",
                )
            )

            score_rows = list(
                ScoreEntry.objects.filter(
                    game_participant__game__round__tournament=completed_tournament
                ).values_list(
                    "game_participant__tournament_participant_id",
                    "category",
                )
            )

            roll_counts = Counter(
                roll.turn.game_participant.tournament_participant_id
                for roll in roll_rows
            )

            round_roll_counts = Counter(
                (
                    roll.turn.game_participant.tournament_participant_id,
                    roll.turn.game_participant.game.round.number,
                )
                for roll in roll_rows
            )

            score_counts = Counter(row[0] for row in score_rows)
            categories_by_participant = defaultdict(set)

            for participant_id, category in score_rows:
                categories_by_participant[participant_id].add(category)

            assert all(len(roll.values) == 5 for roll in roll_rows)

            expected_categories = {category.value for category in ScoreCategory}

            for participation in participations:
                assert 36 <= roll_counts[participation.pk] <= 108
                assert score_counts[participation.pk] == 36

                assert (
                    categories_by_participant[participation.pk] == expected_categories
                )

                assert all(
                    18 <= round_roll_counts[(participation.pk, round_number)] <= 54
                    for round_number in (1, 2)
                )

            entries = ScoreEntry.objects.filter(
                game_participant__game__round__tournament=completed_tournament
            )

            result_kinds = set(entries.values_list("result_kind", flat=True))

            school_values = set(
                entries.filter(result_kind=ScoreResultKind.SCHOOL_BALANCE).values_list(
                    "value", flat=True
                )
            )

            assert result_kinds == {
                ScoreResultKind.POINTS,
                ScoreResultKind.SCHOOL_BALANCE,
                ScoreResultKind.STRIKE_OFF,
            }

            assert any(value < 0 for value in school_values)
            assert 0 in school_values
            assert any(value > 0 for value in school_values)

            completed_turns = Turn.objects.filter(
                game_participant__game__round__tournament=completed_tournament,
                score_entry__isnull=False,
            ).annotate(roll_count=Count("rolls"))

            figure_points = completed_turns.filter(
                score_entry__result_kind=ScoreResultKind.POINTS,
            ).exclude(
                score_entry__category__in={
                    category.value for category in SCHOOL_CATEGORIES
                }
            )

            assert set(completed_turns.values_list("roll_count", flat=True)) == {
                1,
                2,
                3,
            }

            assert figure_points.filter(roll_count=1).exists()
            assert figure_points.filter(roll_count__gt=1).exists()

        assert len(profile_ids) == 16

        organizer = User.objects.get(username="demo-completed-99-16-organizer")

        featured_profile = User.objects.get(
            username="demo-completed-99-16-p001"
        ).player_profile

        featured = tournament.tournament_participants.get(
            player_profile=featured_profile
        )

        first_round = tournament.rounds.get(number=1)

        comparison_options = get_comparison_options(
            actor=organizer,
            participant_id=featured.player_profile_id,
        )

        assert {item["id"] for item in comparison_options["tournaments"]} == {
            item.pk for item in completed_tournaments
        }

        history_page = get_participant_history_page(
            actor=organizer,
            participant_id=featured.player_profile_id,
            tournament_id=tournament.pk,
            page_number=1,
        )

        first_round_history = get_participant_history_page(
            actor=organizer,
            participant_id=featured.player_profile_id,
            tournament_id=tournament.pk,
            page_number=1,
            round_id=first_round.pk,
        )

        history_count = Roll.objects.filter(
            turn__game_participant__tournament_participant=featured
        ).count()

        first_round_count = Roll.objects.filter(
            turn__game_participant__tournament_participant=featured,
            turn__game_participant__game__round=first_round,
        ).count()

        assert history_page["pagination"]["count"] == history_count
        assert history_page["pagination"]["has_next"] is True
        assert first_round_history["pagination"]["count"] == first_round_count

    elif scenario == "mixed-table-states":
        assert tournament.status == TournamentStatus.ACTIVE
        assert tournament.rounds.count() == 2

        waiting_tables, roll_snapshots = _mixed_state_signature(tournament)
        organizer = User.objects.get(username="demo-mixed-table-states-99-16-organizer")

        dashboard = get_organizer_dashboard(
            actor=organizer,
            tournament_id=tournament.pk,
        )

        assert waiting_tables
        assert roll_snapshots

        assert (
            dashboard["summary"]["completed"]
            == tournament.rounds.get(number=1).games.count()
        )

        assert dashboard["summary"]["waiting"] == len(waiting_tables)

    else:
        assert tournament.status == TournamentStatus.ACTIVE
        assert tournament.rounds.count() == 1
