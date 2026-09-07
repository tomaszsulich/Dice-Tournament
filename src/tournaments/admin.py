from collections.abc import Callable

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest

from tournaments.models import Round, Tournament, TournamentOrganizer
from tournaments.services.tournament_lifecycle import (
    complete_tournament,
    open_registration,
    start_tournament,
)


class TournamentOrganizerInline(admin.TabularInline):
    model = TournamentOrganizer
    extra = 0


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    actions = (
        "open_registration_action",
        "start_tournament_action",
        "complete_tournament_action",
    )

    @admin.action(description="Open registration")
    def open_registration_action(
        self, request: HttpRequest, queryset: QuerySet[Tournament]
    ):
        self._run_lifecycle_action(request, queryset, open_registration)

    @admin.action(description="Start tournament")
    def start_tournament_action(
        self, request: HttpRequest, queryset: QuerySet[Tournament]
    ):
        self._run_lifecycle_action(request, queryset, start_tournament)

    @admin.action(description="Complete tournament")
    def complete_tournament_action(
        self, request: HttpRequest, queryset: QuerySet[Tournament]
    ):
        self._run_lifecycle_action(request, queryset, complete_tournament)

    def _run_lifecycle_action(
        self,
        request: HttpRequest,
        queryset: QuerySet[Tournament],
        command: Callable[[Tournament], None],
    ):
        for tournament in queryset:
            try:
                command(tournament)
            except ValidationError as exc:
                self.message_user(request, f"{tournament}: {exc}", level="ERROR")

    list_display = (
        "name",
        "status",
        "registration_mode",
        "event_mode",
        "min_participants",
        "max_participants",
        "starts_at",
    )

    list_filter = (
        "status",
        "registration_mode",
        "event_mode",
    )

    search_fields = ("name",)

    readonly_fields = (
        "status",
        "registration_closed_at",
        "starts_at",
        "completed_at",
        "created_at",
    )

    inlines = (TournamentOrganizerInline,)


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tournament",
        "number",
        "name",
        "status",
        "started_at",
        "ended_at",
    )

    list_filter = ("status", "type")
    search_fields = ("name", "tournament__name")
    ordering = ("tournament", "number")
    readonly_fields = ("status", "started_at", "ended_at")


@admin.register(TournamentOrganizer)
class TournamentOrganizerAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "user",
        "assigned_at",
    )

    search_fields = (
        "tournament__name",
        "user__username",
        "user__email",
    )

    readonly_fields = ("assigned_at",)
