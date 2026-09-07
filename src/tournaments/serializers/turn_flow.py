from rest_framework import serializers

from tournaments.domain.dice.categories import ScoreCategory
from tournaments.domain.tournament.types import TournamentStatus
from tournaments.models import Turn


class HoldDiceCommandSerializer(serializers.Serializer):
    held = serializers.ListField(
        child=serializers.BooleanField(),
        min_length=5,
        max_length=5,
    )

    def validate(self, attrs):
        unknown = set(self.initial_data) - {"held"}

        if unknown:
            raise serializers.ValidationError(
                {field: ["This field is not allowed."] for field in unknown}
            )

        raw_held = self.initial_data.get("held")

        if not isinstance(raw_held, list) or any(
            type(value) is not bool for value in raw_held
        ):
            raise serializers.ValidationError(
                {"held": ["Exactly five boolean values are required."]}
            )

        return attrs


class ChooseCategoryCommandSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=[category.value for category in ScoreCategory]
    )

    pair_value = serializers.IntegerField(min_value=1, max_value=6, required=False)

    def validate(self, attrs):
        unknown = set(self.initial_data) - {"category", "pair_value"}

        if unknown:
            raise serializers.ValidationError(
                {field: ["This field is not allowed."] for field in unknown}
            )

        raw_pair_value = self.initial_data.get("pair_value")

        if "pair_value" in self.initial_data and type(raw_pair_value) is not int:
            raise serializers.ValidationError(
                {"pair_value": ["pair_value must be an integer from 1 to 6."]}
            )

        if "pair_value" in attrs and attrs["category"] != ScoreCategory.PAIR:
            raise serializers.ValidationError(
                {"pair_value": ["pair_value is only valid for Pair."]}
            )

        return attrs


class TurnStateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.IntegerField()
    held_dice = serializers.SerializerMethodField()
    roll_count = serializers.SerializerMethodField()
    can_roll = serializers.SerializerMethodField()

    def get_held_dice(self, turn: Turn):
        return list(turn.held_dice)

    def get_roll_count(self, turn: Turn):
        return turn.rolls.count()

    def get_can_roll(self, turn: Turn):
        user = self.context.get("user")
        owner = turn.game_participant.tournament_participant.player_profile.user
        tournament = turn.game_participant.game.round.tournament

        return (
            user is not None
            and getattr(user, "is_authenticated", False)
            and user.pk == owner.pk
            and tournament.status == TournamentStatus.ACTIVE
            and turn.completed_at is None
            and not hasattr(turn, "score_entry")
            and turn.rolls.count() < 3
        )
