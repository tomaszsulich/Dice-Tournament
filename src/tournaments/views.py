from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from tournaments.domain.tournament.types import ParticipantStatus
from tournaments.models import Game, TournamentParticipant
from tournaments.selectors.game_state import get_game_snapshot
from tournaments.services.connection_state import official_game_for_participant


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participant_table(request: Request, game_id: int) -> HttpResponse:
    try:
        game = Game.objects.select_related("round__tournament").get(pk=game_id)
    except Game.DoesNotExist as exc:
        raise Http404 from exc

    participant = (
        TournamentParticipant.objects.filter(
            tournament=game.round.tournament,
            player_profile__user=request.user,
        )
        .select_related("player_profile")
        .first()
    )

    if participant is None or participant.status != ParticipantStatus.ACTIVE:
        raise Http404

    official_game = official_game_for_participant(participant)

    if official_game is None:
        raise Http404

    if official_game.pk != game.pk:
        return redirect("participant-table", game_id=official_game.pk)

    return render(
        request._request,
        "tournaments/table.html",
        {
            "game_id": game.pk,
            "table_label": game.display_label,
            "table_label_ui": game.display_label.replace(" ", "\u00a0"),
            "initial_snapshot": get_game_snapshot(game=game, user=request.user),
        },
    )
