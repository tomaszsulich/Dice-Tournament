from django.urls import path

from tournaments.api.views import join, leave, tournament_list

urlpatterns = [
    path("tournaments/", tournament_list, name="tournament-list"),
    path("tournaments/<int:tournament_id>/join/", join, name="tournament-join"),
    path("tournaments/<int:tournament_id>/leave/", leave, name="tournament-leave"),
]
