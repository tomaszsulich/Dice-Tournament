from secrets import SystemRandom

import pytest

from tournaments.domain.dice.randomizer import DiceRandomizer

pytestmark = pytest.mark.unit


def test_system_random_satisfies_randomizer_protocol():
    rng: DiceRandomizer = SystemRandom()
    assert 1 <= rng.randint(1, 6) <= 6
