import pytest

from accounts.tests.factories import PlayerProfileFactory
from tournaments.domain.tournament.types import (
    EventMode,
)
from tournaments.models import (
    IdempotencyRecord,
    Roll,
)
from tournaments.services.dice.roll_dice import (
    InvalidRollPayload,
    RollForbidden,
    RollUnavailable,
    execute_roll,
)
from tournaments.services.idempotency import IdempotencyConflict
from tournaments.tests.helpers import FakeRandomizer


@pytest.mark.django_db
def test_remote_first_roll_uses_backend_rng_for_all_five_dice(roll_setup):
    user, game, _turn = roll_setup()
    rng = FakeRandomizer([1, 2, 3, 4, 5])

    response = execute_roll(
        user=user,
        game_id=game.pk,
        payload={},
        key="remote-1",
        rng=rng,
        publisher=lambda _event, _payload: None,
    )

    assert response["values"] == [1, 2, 3, 4, 5]
    assert response["held_after_roll"] == [False] * 5
    assert rng.calls == 5


@pytest.mark.django_db
def test_remote_second_roll_randomizes_only_unheld_positions(roll_setup):
    user, game, turn = roll_setup()

    Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    turn.held_die_1 = True
    turn.held_die_3 = True
    turn.save(update_fields=["held_die_1", "held_die_3"])
    rng = FakeRandomizer([6, 6, 6])

    response = execute_roll(
        user=user,
        game_id=game.pk,
        payload={},
        key="remote-2",
        rng=rng,
        publisher=lambda _event, _payload: None,
    )

    assert response["values"] == [1, 6, 3, 6, 6]
    assert response["held_after_roll"] == [True, False, True, False, False]
    assert rng.calls == 3


@pytest.mark.django_db
def test_stationary_roll_accepts_exactly_five_physical_values_without_rng(roll_setup):
    user, game, _turn = roll_setup(EventMode.IN_PERSON)
    rng = FakeRandomizer([])

    response = execute_roll(
        user=user,
        game_id=game.pk,
        payload={"values": [6, 5, 4, 3, 2]},
        key="physical-1",
        rng=rng,
        publisher=lambda _event, _payload: None,
    )

    assert response["values"] == [6, 5, 4, 3, 2]
    assert rng.calls == 0


@pytest.mark.django_db
def test_stationary_reroll_cannot_change_held_physical_die(roll_setup):
    user, game, turn = roll_setup(EventMode.IN_PERSON)

    Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    turn.held_die_1 = True
    turn.save(update_fields=["held_die_1"])

    with pytest.raises(InvalidRollPayload):
        execute_roll(
            user=user,
            game_id=game.pk,
            payload={"values": [6, 2, 3, 4, 5]},
            key="physical-2",
            rng=FakeRandomizer([]),
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_remote_rejects_client_values(roll_setup):
    user, game, _turn = roll_setup()

    with pytest.raises(InvalidRollPayload):
        execute_roll(
            user=user,
            game_id=game.pk,
            payload={"values": [1, 2, 3, 4, 5]},
            key="remote-values",
            rng=FakeRandomizer([1, 2, 3, 4, 5]),
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_same_key_and_payload_replays_saved_response_without_new_roll(roll_setup):
    user, game, _turn = roll_setup()
    rng = FakeRandomizer([1, 2, 3, 4, 5])

    kwargs = {
        "user": user,
        "game_id": game.pk,
        "payload": {},
        "key": "retry",
        "rng": rng,
        "publisher": lambda _event, _payload: None,
    }

    first = execute_roll(**kwargs)
    second = execute_roll(**kwargs)

    assert second == first
    assert Roll.objects.count() == 1
    assert IdempotencyRecord.objects.count() == 1
    assert rng.calls == 5


@pytest.mark.django_db
def test_same_key_with_different_payload_is_conflict(roll_setup):
    user, game, _turn = roll_setup(EventMode.IN_PERSON)

    execute_roll(
        user=user,
        game_id=game.pk,
        payload={"values": [1, 2, 3, 4, 5]},
        key="same-key",
        rng=FakeRandomizer([]),
        publisher=lambda _event, _payload: None,
    )

    with pytest.raises(IdempotencyConflict):
        execute_roll(
            user=user,
            game_id=game.pk,
            payload={"values": [6, 2, 3, 4, 5]},
            key="same-key",
            rng=FakeRandomizer([]),
            publisher=lambda _event, _payload: None,
        )

    assert Roll.objects.count() == 1


@pytest.mark.django_db
def test_new_key_may_produce_identical_dice(roll_setup):
    user, game, _turn = roll_setup()
    rng = FakeRandomizer([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

    common = {
        "user": user,
        "game_id": game.pk,
        "payload": {},
        "rng": rng,
        "publisher": lambda _event, _payload: None,
    }

    first = execute_roll(key="one", **common)
    second = execute_roll(key="two", **common)

    assert first["values"] == second["values"] == [1, 1, 1, 1, 1]
    assert Roll.objects.count() == 2


@pytest.mark.django_db
def test_fourth_roll_is_rejected(roll_setup):
    user, game, turn = roll_setup()

    for number in range(1, 4):
        Roll.objects.create(
            turn=turn,
            roll_number=number,
            die_1=1,
            die_2=2,
            die_3=3,
            die_4=4,
            die_5=5,
        )

    with pytest.raises(RollUnavailable):
        execute_roll(
            user=user,
            game_id=game.pk,
            payload={},
            key="fourth",
            rng=FakeRandomizer([1] * 5),
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_other_user_cannot_roll_active_participants_turn(roll_setup):
    _user, game, _turn = roll_setup()
    other = PlayerProfileFactory.create().user

    with pytest.raises(RollForbidden):
        execute_roll(
            user=other,
            game_id=game.pk,
            payload={},
            key="other-user",
            rng=FakeRandomizer([1] * 5),
            publisher=lambda _event, _payload: None,
        )


@pytest.mark.django_db
def test_three_legal_rolls_are_numbered_one_two_three(roll_setup):
    user, game, _turn = roll_setup()
    rng = FakeRandomizer([1] * 15)

    for number in range(1, 4):
        response = execute_roll(
            user=user,
            game_id=game.pk,
            payload={},
            key=f"roll-{number}",
            rng=rng,
            publisher=lambda _event, _payload: None,
        )

        assert response["roll_number"] == number

    assert list(
        Roll.objects.order_by("roll_number").values_list("roll_number", flat=True)
    ) == [1, 2, 3]


@pytest.mark.django_db
def test_rollback_does_not_publish_or_keep_roll(roll_setup, monkeypatch):
    user, game, _turn = roll_setup()
    published = []

    def fail_create(**_kwargs):
        raise RuntimeError("forced idempotency failure")

    monkeypatch.setattr(IdempotencyRecord.objects, "create", fail_create)

    with pytest.raises(RuntimeError, match="forced idempotency failure"):
        execute_roll(
            user=user,
            game_id=game.pk,
            payload={},
            key="rollback",
            rng=FakeRandomizer([1, 2, 3, 4, 5]),
            publisher=lambda event, payload: published.append((event, payload)),
        )

    assert Roll.objects.count() == 0
    assert published == []
