from rest_framework import serializers

from tournaments.serializers.turn_flow import TurnStateSerializer


class RollResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    turn_id = serializers.IntegerField()
    roll_number = serializers.IntegerField()
    values = serializers.ListField(child=serializers.IntegerField())
    held_after_roll = serializers.ListField(child=serializers.BooleanField())


class HoldResultSerializer(serializers.Serializer):
    turn_id = serializers.IntegerField()
    held_dice = serializers.ListField(child=serializers.BooleanField())
    can_roll = serializers.BooleanField()


class ScoreEntryResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    turn_id = serializers.IntegerField()
    category = serializers.CharField()
    result_kind = serializers.CharField()
    value = serializers.IntegerField(allow_null=True)


class ParticipantScoreResultSerializer(serializers.Serializer):
    game_participant_id = serializers.IntegerField()
    raw_score = serializers.IntegerField()
    school_balance = serializers.IntegerField()
    figure_points = serializers.IntegerField()
    bonus_points = serializers.IntegerField()
    final_score = serializers.IntegerField()
    is_completed = serializers.BooleanField()


class ChooseCategoryResultSerializer(serializers.Serializer):
    score_entry = ScoreEntryResultSerializer()
    participant_score = ParticipantScoreResultSerializer()
    next_turn_id = serializers.IntegerField(allow_null=True)
    game_complete = serializers.BooleanField()


class GameStateResultSerializer(serializers.Serializer):
    game_id = serializers.IntegerField()
    game_complete = serializers.BooleanField()
    turn = TurnStateSerializer(allow_null=True)


class TournamentDetailResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()


class TournamentLifecycleResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()


class TournamentRankingRowSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    participant_id = serializers.IntegerField()
    total_score = serializers.IntegerField()
    round_scores = serializers.ListField(child=serializers.IntegerField())


class RoundBarrierResultSerializer(serializers.Serializer):
    state = serializers.CharField()
    round_id = serializers.IntegerField(allow_null=True)
    tied_participant_ids = serializers.ListField(child=serializers.IntegerField())


class RoundDrawResultSerializer(serializers.Serializer):
    state = serializers.CharField()
    round_id = serializers.IntegerField(allow_null=True)
    select_participant_id = serializers.IntegerField(allow_null=True)
