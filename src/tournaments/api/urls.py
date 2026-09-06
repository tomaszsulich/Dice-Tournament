from django.urls import path

from tournaments.api.views import join, leave, roll_game, tournament_list

urlpatterns = [
    path("games/<int:game_id>/roll/", roll_game, name="game-roll"),
    path("tournaments/", tournament_list, name="tournament-list"),
    path("tournaments/<int:tournament_id>/join/", join, name="tournament-join"),
    path("tournaments/<int:tournament_id>/leave/", leave, name="tournament-leave"),
]
