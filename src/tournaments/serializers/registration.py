from collections.abc import Mapping

from rest_framework import serializers

from tournaments.models import Tournament


class EmptyRegistrationCommandSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError("Expected a JSON object.")

        if data:
            raise serializers.ValidationError(
                {field: ["This field is not allowed."] for field in sorted(data.keys())}
            )

        return {}


class OpenTournamentSerializer(serializers.ModelSerializer):
    available_places = serializers.SerializerMethodField()

    class Meta:
        model = Tournament

        fields = (
            "id",
            "name",
            "registration_deadline",
            "starts_at",
            "timezone",
            "max_participants",
            "available_places",
            "group_rounds",
            "table_size",
            "poker_scoring_variant",
            "event_mode",
        )

        read_only_fields = fields

    def get_available_places(self, obj) -> int:
        return max(0, obj.max_participants - obj.registered_count)
