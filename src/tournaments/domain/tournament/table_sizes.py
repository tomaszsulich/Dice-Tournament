from dataclasses import dataclass
from math import ceil

MIN_TABLE_SIZE = 2
MAX_TABLE_SIZE = 6
MAX_ACTIVE_PARTICIPANTS = 128


class TableSizePlanningError(ValueError):
    """Raised when participants cannot be assigned to legal tables."""


@dataclass
class TableSizePlan:
    total: int
    sizes: tuple[int, ...]
    table_count: int


def compute_balanced_table_sizes(
    n: int,
    preferred_size: int,
) -> TableSizePlan:
    if n > MAX_ACTIVE_PARTICIPANTS:
        raise TableSizePlanningError(
            f"Active participants cannot exceed {MAX_ACTIVE_PARTICIPANTS}."
        )

    if not MIN_TABLE_SIZE <= preferred_size <= MAX_TABLE_SIZE:
        raise TableSizePlanningError(
            "Preferred table size must be between "
            f"{MIN_TABLE_SIZE} and {MAX_TABLE_SIZE}."
        )

    if n < MIN_TABLE_SIZE:
        raise TableSizePlanningError(
            "Participants cannot be partitioned into legal tables."
        )

    if n <= MAX_TABLE_SIZE:
        return TableSizePlan(
            total=n,
            sizes=(n,),
            table_count=1,
        )

    table_count = ceil(n / preferred_size)

    while n // table_count < MIN_TABLE_SIZE:
        table_count -= 1

    base_size, remainder = divmod(n, table_count)

    sizes = (base_size + 1,) * remainder + (base_size,) * (table_count - remainder)

    if (
        min(sizes) < MIN_TABLE_SIZE
        or max(sizes) > MAX_TABLE_SIZE
        or max(sizes) - min(sizes) > 1
        or sum(sizes) != n
    ):
        raise TableSizePlanningError(
            "Participants cannot be partitioned into legal tables."
        )

    return TableSizePlan(
        total=n,
        sizes=sizes,
        table_count=table_count,
    )
