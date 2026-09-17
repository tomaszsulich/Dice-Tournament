from rest_framework import serializers

from accounts.models import PlayerProfile


class PlayerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerProfile

        fields = (
            "id",
            "display_name",
            "nickname",
            "created_at",
        )

        read_only_fields = (
            "id",
            "created_at",
        )

    def create(self, validated_data):
        user = self.context["request"].user
        return PlayerProfile.objects.create(user=user, **validated_data)
