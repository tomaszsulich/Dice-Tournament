from django.urls import path

from tournaments.realtime.consumers import (
    OrganizerConsumer,
    ParticipantAssignmentConsumer,
    TableConsumer,
)

websocket_urlpatterns = [
    path("ws/participant/assignments/", ParticipantAssignmentConsumer.as_asgi()),
    path("ws/tables/<int:game_id>/", TableConsumer.as_asgi()),
    path(
        "ws/tournaments/<int:tournament_id>/organizers/",
        OrganizerConsumer.as_asgi(),
    ),
]
