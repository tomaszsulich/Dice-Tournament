from rest_framework import serializers

from tournaments.models import Tournament


class TournamentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = (
            "name",
            "registration_mode",
            "min_participants",
            "max_participants",
            "registration_deadline",
            "timezone",
            "group_rounds",
            "table_size",
            "poker_scoring_variant",
            "decision_time_limit",
            "event_mode",
        )


class OrganizerParticipantCommandSerializer(serializers.Serializer):
    player_profile_id = serializers.IntegerField(min_value=1)
    team_label = serializers.CharField(max_length=50, allow_blank=True, required=False)

    starting_number = serializers.IntegerField(
        min_value=1, allow_null=True, required=False
    )

    seeding = serializers.IntegerField(min_value=1, allow_null=True, required=False)
