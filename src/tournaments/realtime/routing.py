from django.urls import path

from tournaments.realtime.consumers import OrganizerConsumer, TableConsumer

websocket_urlpatterns = [
    path("ws/tables/<int:game_id>/", TableConsumer.as_asgi()),
    path(
        "ws/tournaments/<int:tournament_id>/organizers/",
        OrganizerConsumer.as_asgi(),
    ),
]
