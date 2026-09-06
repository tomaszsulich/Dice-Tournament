from secrets import SystemRandom

from tournaments.domain.dice.randomizer import DiceRandomizer


def test_system_random_satisfies_randomizer_protocol():
    rng: DiceRandomizer = SystemRandom()
    assert 1 <= rng.randint(1, 6) <= 6
