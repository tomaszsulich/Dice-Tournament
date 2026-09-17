from django.urls import path

from tournaments.api.views import (
    choose_game_category,
    game_state,
    hold_game_dice,
    join,
    leave,
    roll_game,
    round_barrier,
    round_draw,
    tournament_add_participant,
    tournament_close_registration,
    tournament_complete,
    tournament_create,
    tournament_detail,
    tournament_list,
    tournament_open_registration,
    tournament_ranking,
    tournament_start,
)
from tournaments.organizer_dashboard_views import (
    organizer_dashboard_api,
    participant_comparison_api,
    participant_comparison_history_api,
)

urlpatterns = [
    path(
        "tournaments/<int:tournament_id>/organizer-dashboard/",
        organizer_dashboard_api,
        name="organizer-dashboard-api",
    ),
    path(
        "comparisons/participants/<int:participant_id>/",
        participant_comparison_api,
        name="participant-comparison-api",
    ),
    path(
        "comparisons/participants/<int:participant_id>/history/",
        participant_comparison_history_api,
        name="participant-comparison-history-api",
    ),
    path("rounds/<int:round_id>/barrier/", round_barrier, name="round-barrier"),
    path("rounds/<int:round_id>/draw/", round_draw, name="round-draw"),
    path("games/<int:game_id>/roll/", roll_game, name="game-roll"),
    path("games/<int:game_id>/holds/", hold_game_dice, name="game-holds"),
    path(
        "games/<int:game_id>/choose-category/",
        choose_game_category,
        name="game-choose-category",
    ),
    path("games/<int:game_id>/state/", game_state, name="game-state"),
    path("tournaments/create/", tournament_create, name="tournament-create"),
    path("tournaments/", tournament_list, name="tournament-list"),
    path(
        "tournaments/<int:tournament_id>/",
        tournament_detail,
        name="tournament-detail",
    ),
    path(
        "tournaments/<int:tournament_id>/open-registration/",
        tournament_open_registration,
        name="tournament-open-registration",
    ),
    path(
        "tournaments/<int:tournament_id>/close-registration/",
        tournament_close_registration,
        name="tournament-close-registration",
    ),
    path(
        "tournaments/<int:tournament_id>/participants/",
        tournament_add_participant,
        name="tournament-add-participant",
    ),
    path(
        "tournaments/<int:tournament_id>/start/",
        tournament_start,
        name="tournament-start",
    ),
    path(
        "tournaments/<int:tournament_id>/complete/",
        tournament_complete,
        name="tournament-complete",
    ),
    path(
        "tournaments/<int:tournament_id>/ranking/",
        tournament_ranking,
        name="tournament-ranking",
    ),
    path("tournaments/<int:tournament_id>/join/", join, name="tournament-join"),
    path("tournaments/<int:tournament_id>/leave/", leave, name="tournament-leave"),
]
