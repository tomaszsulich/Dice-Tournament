from collections.abc import Mapping

from rest_framework import serializers


class EmptyLifecycleCommandSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError("Expected a JSON object.")

        if data:
            raise serializers.ValidationError(
                {field: ["This field is not allowed."] for field in sorted(data)}
            )

        return {}


class DrawCommandSerializer(serializers.Serializer):
    reason = serializers.CharField(
        max_length=500, allow_blank=False, trim_whitespace=True
    )
