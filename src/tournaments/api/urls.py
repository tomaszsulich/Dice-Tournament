from django.urls import path

from tournaments.api.views import (
    choose_game_category,
    game_state,
    hold_game_dice,
    join,
    leave,
    roll_game,
    tournament_list,
)

urlpatterns = [
    path("games/<int:game_id>/roll/", roll_game, name="game-roll"),
    path("games/<int:game_id>/holds/", hold_game_dice, name="game-holds"),
    path(
        "games/<int:game_id>/choose-category/",
        choose_game_category,
        name="game-choose-category",
    ),
    path("games/<int:game_id>/state/", game_state, name="game-state"),
    path("tournaments/", tournament_list, name="tournament-list"),
    path("tournaments/<int:tournament_id>/join/", join, name="tournament-join"),
    path("tournaments/<int:tournament_id>/leave/", leave, name="tournament-leave"),
]
