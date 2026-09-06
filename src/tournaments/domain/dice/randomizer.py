from typing import Protocol


class DiceRandomizer(Protocol):
    def randint(self, a: int, b: int) -> int: ...
