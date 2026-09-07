from tournaments.services.ranking import CompletedResult, build_ranking


def test_ranking_orders_by_total_score_before_round_scores():
    ranking = build_ranking(
        [
            CompletedResult(1, 35),
            CompletedResult(1, 10),  # total 45, best round 35
            CompletedResult(2, 30),
            CompletedResult(2, 20),  # total 50, best round 30
        ]
    )

    assert [row.participant_id for row in ranking] == [2, 1]
    assert [row.total_score for row in ranking] == [50, 45]


def test_ranking_uses_descending_round_scores_for_equal_totals():
    ranking = build_ranking(
        [
            CompletedResult(1, 20),
            CompletedResult(1, 10),
            CompletedResult(2, 18),
            CompletedResult(2, 12),
            CompletedResult(3, 30),
            CompletedResult(3, 0),
        ]
    )

    assert [row.participant_id for row in ranking] == [3, 1, 2]
    assert [row.round_scores for row in ranking] == [(30, 0), (20, 10), (18, 12)]


def test_ranking_uses_later_lexicographic_score_when_earlier_scores_are_equal():
    ranking = build_ranking(
        [
            CompletedResult(1, 30),
            CompletedResult(1, 20),
            CompletedResult(1, 10),
            CompletedResult(2, 30),
            CompletedResult(2, 18),
            CompletedResult(2, 12),
        ]
    )

    assert [row.participant_id for row in ranking] == [1, 2]

    assert [row.round_scores for row in ranking] == [
        (30, 20, 10),
        (30, 18, 12),
    ]


def test_ranking_assigns_consecutive_positions_without_ties():
    ranking = build_ranking(
        [
            CompletedResult(1, 30),
            CompletedResult(2, 20),
            CompletedResult(3, 10),
        ]
    )

    assert [row.position for row in ranking] == [1, 2, 3]


def test_ranking_preserves_true_ex_aequo():
    ranking = build_ranking(
        [
            CompletedResult(1, 20),
            CompletedResult(1, 10),
            CompletedResult(2, 10),
            CompletedResult(2, 20),
            CompletedResult(3, 5),
        ]
    )

    assert [row.participant_id for row in ranking] == [1, 2, 3]
    assert [row.position for row in ranking] == [1, 1, 3]


def test_ranking_returns_empty_tuple_for_no_results():
    assert build_ranking([]) == ()
