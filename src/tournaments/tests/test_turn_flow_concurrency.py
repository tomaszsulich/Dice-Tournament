from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from tournaments.domain.dice.categories import ScoreCategory
from tournaments.models import Roll, ScoreEntry, Turn
from tournaments.services.dice.select_category import select_category


@pytest.mark.django_db(transaction=True)
def test_two_concurrent_category_retries_score_and_advance_once(roll_setup):
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

    barrier = Barrier(2)

    def worker():
        close_old_connections()
        barrier.wait()

        try:
            return select_category(
                user=user,
                game_id=game.pk,
                payload={"category": ScoreCategory.CHANCE},
                key="concurrent-category-retry",
                publisher=lambda _event, _payload: None,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: worker(), range(2)))

    assert responses[0] == responses[1]
    assert (
        ScoreEntry.objects.filter(game_participant=turn.game_participant).count() == 1
    )
    assert Turn.objects.filter(game_participant=turn.game_participant).count() == 2
