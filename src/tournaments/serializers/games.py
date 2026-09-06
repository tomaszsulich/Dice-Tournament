from rest_framework import serializers

from tournaments.models import Game


class GameSerializer(serializers.ModelSerializer):
    display_label = serializers.CharField(read_only=True)

    class Meta:
        model = Game

        fields = (
            "id",
            "round",
            "display_number",
            "display_label",
        )

        read_only_fields = fields
