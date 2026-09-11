from rest_framework import serializers


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


class ScorecardParticipantSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    is_current_user = serializers.BooleanField()
    is_active = serializers.BooleanField()
    total_score = serializers.IntegerField()
    scores = serializers.DictField()


class ScorecardCategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    information = serializers.CharField(allow_null=True)
    selection_options = serializers.ListField(child=serializers.IntegerField())


class ScorecardSectionSerializer(serializers.Serializer):
    label = serializers.CharField()
    information = serializers.CharField()


class GameTurnSnapshotSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.IntegerField()
    roll_count = serializers.IntegerField()
    can_roll = serializers.BooleanField()
    can_hold = serializers.BooleanField()
    selectable_category_ids = serializers.ListField(child=serializers.CharField())
    held_dice = serializers.ListField(child=serializers.BooleanField())
    dice = serializers.ListField(child=serializers.IntegerField(allow_null=True))
    dice_total = serializers.IntegerField(allow_null=True)
    rerolls_remaining = serializers.IntegerField(allow_null=True)
    is_current_user = serializers.BooleanField()
    category_required = serializers.BooleanField()


class GameStateResultSerializer(serializers.Serializer):
    game_id = serializers.IntegerField()
    state_version = serializers.IntegerField()
    event_mode = serializers.CharField()
    game_complete = serializers.BooleanField()
    participation_ongoing = serializers.BooleanField()
    participants = ScorecardParticipantSerializer(many=True)
    category_sections = serializers.DictField(child=ScorecardSectionSerializer())
    categories = ScorecardCategorySerializer(many=True)
    turn = GameTurnSnapshotSerializer(allow_null=True)


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
    selected_participant_id = serializers.IntegerField(allow_null=True)
