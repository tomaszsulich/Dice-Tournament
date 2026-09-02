import pytest

from accounts.serializers import PlayerProfileSerializer
from accounts.tests.factories import PlayerProfileFactory


@pytest.mark.unit
def test_player_profile_serializer_returns_profile_data():
    profile = PlayerProfileFactory.build(
        id=1,
        display_name="Jan Kowalski",
        nickname="DiceFox",
    )

    serializer = PlayerProfileSerializer(profile)

    assert serializer.data["id"] == 1
    assert serializer.data["display_name"] == "Jan Kowalski"
    assert serializer.data["nickname"] == "DiceFox"


@pytest.mark.unit
def test_player_profile_serializer_does_not_expose_user():
    profile = PlayerProfileFactory.build()
    serializer = PlayerProfileSerializer(profile)
    assert "user" not in serializer.data
