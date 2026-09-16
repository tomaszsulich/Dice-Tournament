from __future__ import annotations

import os
import secrets

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection, transaction

from tournaments.demo_builders import (
    SUPPORTED_DEMO_SCENARIOS,
    SUPPORTED_DEMO_SIZES,
    DemoWorldBuilder,
    delete_demo_namespace,
)

DEMO_APP_LABELS = ("accounts", "tournaments")
OPTIONAL_RUNTIME_TABLES = ("django_session",)


class Command(BaseCommand):
    help = "Create local demo data with seed-reproducible content for the MVP."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--size", type=int, required=True)
        parser.add_argument("--scenario", required=True)
        parser.add_argument("--seed", type=int, required=True)

        reset_group = parser.add_mutually_exclusive_group()

        reset_group.add_argument(
            "--reset",
            action="store_true",
            help="Replace only the matching demo namespace before rebuilding it.",
        )

        reset_group.add_argument(
            "--reset-database",
            action="store_true",
            help=(
                "Delete all local application data, restart PostgreSQL identities "
                "and then build the requested demo world."
            ),
        )

    def handle(self, *args, **options) -> None:
        self._require_demo_seed_enabled()

        size = options["size"]
        scenario = options["scenario"]
        seed = options["seed"]

        if size not in SUPPORTED_DEMO_SIZES:
            raise CommandError("--size must be one of: 16, 64, 128.")

        if scenario not in SUPPORTED_DEMO_SCENARIOS:
            choices = ", ".join(sorted(SUPPORTED_DEMO_SCENARIOS))
            raise CommandError(f"--scenario must be one of: {choices}.")

        password = os.getenv("DEMO_PASSWORD") or secrets.token_urlsafe(18)

        try:
            with transaction.atomic():
                if options["reset_database"]:
                    self._reset_development_database()

                elif options["reset"]:
                    delete_demo_namespace(
                        scenario=scenario,
                        seed=seed,
                        size=size,
                    )

                world = DemoWorldBuilder(
                    size=size,
                    scenario=scenario,
                    seed=seed,
                    password=password,
                ).build()

        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Demo world created."))
        self.stdout.write(f"namespace={world.namespace}")
        self.stdout.write(f"organizer={world.organizer_username}")

        self.stdout.write(f"tournament_id={world.tournament_id}")
        self.stdout.write(f"participants={world.participant_count}")

        self.stdout.write(f"tables={world.table_count}")
        self.stdout.write(f"demo_password={password}")

        self.stdout.write(
            self.style.WARNING(
                "The demo password is local-only. "
                "Do not include it in captured evidence."
            )
        )

    @staticmethod
    def _require_demo_seed_enabled() -> None:
        if not getattr(settings, "ALLOW_DEMO_SEED", False):
            raise CommandError("Demo seeding is disabled. Set ALLOW_DEMO_SEED=true.")

        if not settings.DEBUG:
            raise CommandError("Demo seeding is forbidden when DEBUG is false.")

    def _reset_development_database(self) -> None:
        """Clear local application data and restart PostgreSQL-owned identities."""
        if connection.vendor != "postgresql":
            raise CommandError("--reset-database requires PostgreSQL.")

        existing_tables = set(connection.introspection.table_names())
        tables_to_truncate: set[str] = set()

        for app_label in DEMO_APP_LABELS:
            app_config = apps.get_app_config(app_label)

            for model in app_config.get_models(include_auto_created=True):
                table_name = model._meta.db_table

                if model._meta.managed and table_name in existing_tables:
                    tables_to_truncate.add(table_name)

        tables_to_truncate.update(
            table_name
            for table_name in OPTIONAL_RUNTIME_TABLES
            if table_name in existing_tables
        )

        if not tables_to_truncate:
            raise CommandError("No application tables were found to reset.")

        quote_name = connection.ops.quote_name

        table_sql = ", ".join(
            quote_name(table_name) for table_name in sorted(tables_to_truncate)
        )

        with connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {table_sql} RESTART IDENTITY CASCADE")

        self.stdout.write(
            self.style.WARNING(
                "Local application data cleared; PostgreSQL identities restarted."
            )
        )
