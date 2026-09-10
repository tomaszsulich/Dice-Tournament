import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.tests.factories import PlayerProfileFactory
from tournaments.domain.dice.categories import ScoreCategory
from tournaments.models import Roll, ScoreEntry, ScoreResultKind


@pytest.mark.django_db
def test_holds_api_requires_exactly_five_booleans(api_client, roll_setup):
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

    api_client.force_authenticate(user=user)
    path = f"/api/games/{game.pk}/holds/"

    short = api_client.post(path, {"held": [True, False]}, format="json")

    numeric = api_client.post(
        path,
        {"held": [True, False, 1, False, False]},
        format="json",
    )

    assert short.status_code == status.HTTP_400_BAD_REQUEST
    assert numeric.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_holds_api_updates_current_state(api_client, roll_setup):
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

    api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/games/{game.pk}/holds/",
        {"held": [True, False, True, False, False]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["held_dice"] == [True, False, True, False, False]
    assert response.data["can_roll"] is True


@pytest.mark.django_db
def test_choose_category_rejects_client_owned_identity_and_points(
    api_client, roll_setup
):
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

    api_client.force_authenticate(user=user)
    path = f"/api/games/{game.pk}/choose-category/"

    response = api_client.post(
        path,
        {
            "category": ScoreCategory.CHANCE,
            "player_id": user.pk,
            "points": 999,
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="bad-owned-fields",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "player_id" in response.data
    assert "points" in response.data
    assert not ScoreEntry.objects.exists()


@pytest.mark.django_db
def test_choose_category_api_replays_accepted_command(api_client, roll_setup):
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

    api_client.force_authenticate(user=user)

    request = {
        "path": f"/api/games/{game.pk}/choose-category/",
        "data": {"category": ScoreCategory.CHANCE},
        "format": "json",
        "HTTP_IDEMPOTENCY_KEY": "category-retry",
    }

    first = api_client.post(**request)
    second = api_client.post(**request)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED
    assert second.data == first.data
    assert ScoreEntry.objects.count() == 1


@pytest.mark.django_db
def test_other_user_cannot_choose_category(api_client, roll_setup):
    _user, game, turn = roll_setup()

    Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=1,
        die_2=2,
        die_3=3,
        die_4=4,
        die_5=5,
    )

    other = PlayerProfileFactory.create().user
    api_client.force_authenticate(user=other)

    response = api_client.post(
        f"/api/games/{game.pk}/choose-category/",
        {"category": ScoreCategory.CHANCE},
        format="json",
        HTTP_IDEMPOTENCY_KEY="foreign-category",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "NOT_YOUR_TURN"


@pytest.mark.django_db
def test_game_state_calculates_can_roll_instead_of_persisting_it(
    api_client, roll_setup
):
    user, game, turn = roll_setup()
    api_client.force_authenticate(user=user)
    path = f"/api/games/{game.pk}/state/"

    initial = api_client.get(path)

    assert initial.status_code == status.HTTP_200_OK
    assert initial.data["turn"]["can_roll"] is True
    assert initial.data["turn"]["roll_count"] == 0

    for number in range(1, 4):
        Roll.objects.create(
            turn=turn,
            roll_number=number,
            die_1=1,
            die_2=2,
            die_3=3,
            die_4=4,
            die_5=5,
        )

    after_third = api_client.get(path)

    assert after_third.data["turn"]["can_roll"] is False
    assert after_third.data["turn"]["roll_count"] == 3


@pytest.mark.django_db
def test_game_state_displays_zero_school_balance_as_x(api_client, roll_setup):
    user, game, turn = roll_setup()
    participant = turn.game_participant

    ScoreEntry.objects.create(
        turn=turn,
        game_participant=participant,
        category=ScoreCategory.ONES,
        result_kind=ScoreResultKind.SCHOOL_BALANCE,
        value=0,
    )

    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/games/{game.pk}/state/")

    assert response.status_code == status.HTTP_200_OK

    row = next(
        item for item in response.data["participants"] if item["id"] == participant.pk
    )

    assert row["scores"][ScoreCategory.ONES] == "X"


@pytest.mark.django_db
def test_game_state_exposes_pair_subselection_without_scoring_in_frontend(
    api_client, roll_setup
):
    user, game, turn = roll_setup()

    Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=3,
        die_2=3,
        die_3=3,
        die_4=5,
        die_5=5,
    )

    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/games/{game.pk}/state/")

    assert response.status_code == status.HTTP_200_OK

    pair = next(
        category
        for category in response.data["categories"]
        if category["id"] == ScoreCategory.PAIR
    )

    assert pair["selection_options"] == [3, 5]

    chance = next(
        category
        for category in response.data["categories"]
        if category["id"] == ScoreCategory.CHANCE
    )

    assert chance["selection_options"] == []


@pytest.mark.django_db
def test_choose_category_rejects_boolean_pair_value(api_client, roll_setup):
    user, game, turn = roll_setup()

    Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=3,
        die_2=3,
        die_3=3,
        die_4=5,
        die_5=5,
    )

    api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/games/{game.pk}/choose-category/",
        {"category": ScoreCategory.PAIR, "pair_value": True},
        format="json",
        HTTP_IDEMPOTENCY_KEY="boolean-pair-value",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "pair_value" in response.data
    assert not ScoreEntry.objects.exists()


@pytest.mark.django_db
def test_game_state_displays_strike_off_as_x(roll_setup):
    user, game, turn = roll_setup()

    ScoreEntry.objects.create(
        turn=turn,
        game_participant=turn.game_participant,
        category=ScoreCategory.PAIR,
        result_kind=ScoreResultKind.STRIKE_OFF,
        value=None,
    )

    client = APIClient()
    client.force_authenticate(user)
    response = client.get(reverse("game-state", args=[game.pk]))

    assert response.status_code == 200

    row = next(
        participant
        for participant in response.data["participants"]
        if participant["id"] == turn.game_participant.pk
    )

    assert row["scores"][ScoreCategory.PAIR] == "X"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("category", "dice", "expected_points"),
    [
        (ScoreCategory.PAIR, (6, 6, 1, 2, 3), 24),
        (ScoreCategory.TWO_PAIRS, (6, 6, 4, 4, 1), 40),
        (ScoreCategory.TWO_PAIRS, (4, 4, 4, 4, 1), 32),
        (ScoreCategory.TRIPLE, (5, 5, 5, 2, 3), 30),
        (ScoreCategory.QUAD, (4, 4, 4, 4, 2), 32),
        (ScoreCategory.FULL, (3, 3, 3, 5, 5), 38),
        (ScoreCategory.EVEN, (2, 2, 4, 4, 6), 36),
        (ScoreCategory.ODD, (1, 1, 3, 5, 5), 30),
        (ScoreCategory.SMALL_STRAIGHT, (1, 2, 3, 4, 5), 30),
        (ScoreCategory.LARGE_STRAIGHT, (2, 3, 4, 5, 6), 40),
        (ScoreCategory.GAP, (1, 2, 3, 4, 6), 32),
        (ScoreCategory.CHANCE, (1, 2, 2, 5, 6), 32),
        (ScoreCategory.POKER, (6, 6, 6, 6, 6), 200),
    ],
)
def test_first_roll_figure_scoring_preserves_full_roll_snapshot(
    api_client,
    roll_setup,
    category,
    dice,
    expected_points,
):
    user, game, turn = roll_setup()

    roll = Roll.objects.create(
        turn=turn,
        roll_number=1,
        die_1=dice[0],
        die_2=dice[1],
        die_3=dice[2],
        die_4=dice[3],
        die_5=dice[4],
    )

    api_client.force_authenticate(user=user)

    response = api_client.post(
        f"/api/games/{game.pk}/choose-category/",
        {"category": category},
        format="json",
        HTTP_IDEMPOTENCY_KEY=f"snapshot-{category}",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["score_entry"]["value"] == expected_points

    roll.refresh_from_db()

    assert roll.values == dice
    assert Roll.objects.filter(turn=turn).count() == 1
