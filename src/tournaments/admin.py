from django.contrib import admin

from tournaments.models import Round, Tournament, TournamentOrganizer


class TournamentOrganizerInline(admin.TabularInline):
    model = TournamentOrganizer
    extra = 0


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
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
