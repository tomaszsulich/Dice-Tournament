SCHOOL_FAILURE_PENALTY = 50
FIGURE_COMPLETION_BONUS = 100


def apply_school_penalty(balance: int) -> int:
    if balance < 0:
        return balance - SCHOOL_FAILURE_PENALTY
    return balance


def figure_completion_bonus(*, all_completed: bool, has_strike_off: bool) -> int:
    if all_completed and not has_strike_off:
        return FIGURE_COMPLETION_BONUS
    return 0
