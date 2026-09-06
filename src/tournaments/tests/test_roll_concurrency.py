from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from tournaments.models import Roll
from tournaments.services.dice.roll_dice import execute_roll
from tournaments.tests.test_roll_service import FakeRandomizer


@pytest.mark.django_db(transaction=True)
def test_two_concurrent_retries_create_exactly_one_roll(roll_setup):
    user, game, _turn = roll_setup()
    barrier = Barrier(2)

    def worker():
        close_old_connections()
        barrier.wait()

        try:
            return execute_roll(
                user=user,
                game_id=game.pk,
                payload={},
                key="concurrent-retry",
                rng=FakeRandomizer([1, 2, 3, 4, 5]),
                publisher=lambda _event, _payload: None,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: worker(), range(2)))

    assert responses[0] == responses[1]
    assert Roll.objects.filter(turn__game_participant__game=game).count() == 1
