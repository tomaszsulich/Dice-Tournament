from django.http import Http404, HttpResponse
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from tournaments.models import Game
from tournaments.selectors.game_state import get_game_snapshot


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participant_table(request: Request, game_id: int) -> HttpResponse:
    try:
        game = Game.objects.select_related("round__tournament").get(pk=game_id)
    except Game.DoesNotExist as exc:
        raise Http404 from exc

    allowed = game.game_participants.filter(
        tournament_participant__player_profile__user=request.user
    ).exists()

    if not allowed:
        raise Http404

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
