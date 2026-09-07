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
    tournament_complete,
    tournament_detail,
    tournament_list,
    tournament_open_registration,
    tournament_ranking,
    tournament_start,
)

urlpatterns = [
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
