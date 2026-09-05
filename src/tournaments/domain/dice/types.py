from collections.abc import Iterable

type Dice = tuple[int, int, int, int, int]

DICE_COUNT = 5
MIN_DIE_VALUE = 1
MAX_DIE_VALUE = 6


class InvalidDiceError(ValueError):
    """Raised when a dice snapshot does not contain five legal values."""


def make_dice(values: Iterable[int]) -> Dice:
    dice = tuple(values)

    if len(dice) != DICE_COUNT:
        raise InvalidDiceError(f"Exactly {DICE_COUNT} dice are required.")

    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or not MIN_DIE_VALUE <= value <= MAX_DIE_VALUE
        for value in dice
    ):
        raise InvalidDiceError(
            "Each die value must be an integer from "
            f"{MIN_DIE_VALUE} to {MAX_DIE_VALUE}."
        )

    return dice
