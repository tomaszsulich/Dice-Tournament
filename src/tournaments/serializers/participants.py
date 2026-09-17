from rest_framework import serializers

from tournaments.models import TournamentParticipant


class TournamentParticipantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        source="full_name_snapshot",
        read_only=True,
    )

    display_name = serializers.CharField(
        source="display_name_snapshot",
        read_only=True,
    )

    nickname = serializers.CharField(
        source="nickname_snapshot",
        read_only=True,
    )

    class Meta:
        model = TournamentParticipant

        fields = (
            "id",
            "full_name",
            "display_name",
            "nickname",
            "team_label",
            "starting_number",
            "seeding",
            "status",
            "joined_at",
            "total_score",
        )

        read_only_fields = fields
