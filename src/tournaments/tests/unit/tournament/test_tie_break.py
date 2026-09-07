from collections.abc import Sequence

import pytest

from tournaments.domain.tournament.tie_break import controlled_draw, top_material_tie
from tournaments.services.ranking import RankingRow


class FakeChoice:
    def choice(self, values: Sequence[int]) -> int:
        return values[-1]


def test_top_material_tie_returns_only_participants_sharing_first_place():
    ranking = (
        RankingRow(1, 30, (20, 10), 1),
        RankingRow(2, 30, (20, 10), 1),
        RankingRow(3, 29, (20, 9), 3),
    )

    tie = top_material_tie(ranking)

    assert tie is not None
    assert tie.participant_ids == (1, 2)


def test_top_material_tie_returns_none_without_a_first_place_tie():
    ranking = (
        RankingRow(1, 30, (20, 10), 1),
        RankingRow(2, 29, (19, 10), 2),
    )

    assert top_material_tie(ranking) is None


def test_top_material_tie_returns_none_for_empty_ranking():
    assert top_material_tie(()) is None


def test_controlled_draw_uses_injected_choice_source():
    assert controlled_draw((8, 3), FakeChoice()) == 8


def test_controlled_draw_normalizes_candidate_order_and_duplicates():
    assert controlled_draw((8, 3, 8, 5), FakeChoice()) == 8


@pytest.mark.parametrize("participants", [(), (1,), (1, 1)])
def test_controlled_draw_rejects_fewer_than_two_distinct_candidates(participants):
    with pytest.raises(ValueError):
        controlled_draw(participants, FakeChoice())
