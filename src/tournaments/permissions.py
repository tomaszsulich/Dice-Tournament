from rest_framework.permissions import BasePermission

from tournaments.models import TournamentOrganizer


class IsTournamentOrganizer(BasePermission):
    def has_object_permission(self, request, _view, obj):
        return TournamentOrganizer.objects.filter(
            tournament=obj,
            user=request.user,
        ).exists()
