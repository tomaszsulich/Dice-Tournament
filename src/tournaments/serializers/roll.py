from rest_framework import serializers


class RollCommandSerializer(serializers.Serializer):
    values = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=6),
        min_length=5,
        max_length=5,
        required=False,
    )

    def validate(self, attrs):
        unknown = set(self.initial_data) - {"values"}

        if unknown:
            raise serializers.ValidationError(
                {field: ["This field is not allowed."] for field in unknown}
            )

        return attrs
