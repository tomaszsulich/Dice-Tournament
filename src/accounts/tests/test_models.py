import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.models import PlayerProfile
from accounts.tests.factories import PlayerProfileFactory, UserFactory


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_user_can_exist_without_player_profile():
    user = UserFactory.create()
    assert not PlayerProfile.objects.filter(user=user).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_player_profile_is_unique_for_user():
    user = UserFactory.create()
    PlayerProfileFactory.create(user=user)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PlayerProfileFactory.create(user=user)


@pytest.mark.unit
def test_nickname_is_independent_from_display_name():
    profile = PlayerProfileFactory.build(
        display_name="Jan Kowalski",
        nickname="DiceFox",
    )

    assert profile.display_name == "Jan Kowalski"
    assert profile.nickname == "DiceFox"


@pytest.mark.unit
def test_user_preserves_full_name_independently_from_nickname():
    user = UserFactory.build(
        first_name="Jan",
        last_name="Kowalski",
    )

    profile = PlayerProfileFactory.build(
        user=user,
        display_name="Jan Kowalski",
        nickname="DiceFox",
    )

    assert user.first_name == "Jan"
    assert user.last_name == "Kowalski"
    assert profile.nickname == "DiceFox"


@pytest.mark.unit
@pytest.mark.parametrize(
    "nickname",
    [
        "Champion",
        "winner",
        "Mistrz",
        "1 miejsce",
        "pierwsze miejsce",
        "top 3",
        "najlepszy gracz",
    ],
)
def test_profile_rejects_nickname_suggesting_tournament_status(nickname: str):
    profile = PlayerProfileFactory.build(nickname=nickname)

    with pytest.raises(ValidationError):
        profile.full_clean()
