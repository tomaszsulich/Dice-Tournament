import pytest
from django.conf import settings

pytestmark = pytest.mark.unit


def test_celery_uses_two_explicit_queues_and_routes_background_tasks():
    queue_names = {queue.name for queue in settings.CELERY_TASK_QUEUES}

    assert queue_names == {"notifications", "maintenance"}
    assert settings.CELERY_TASK_CREATE_MISSING_QUEUES is False

    assert settings.CELERY_TASK_ROUTES == {
        "tournaments.tasks.notifications.send_tournament_invitation": {
            "queue": "notifications"
        },
        "tournaments.tasks.maintenance.cleanup_expired_idempotency_records": {
            "queue": "maintenance"
        },
        "tournaments.tasks.maintenance.flush_expired_tokens": {"queue": "maintenance"},
    }


def test_beat_schedules_only_maintenance_tasks():
    schedule = settings.CELERY_BEAT_SCHEDULE

    assert schedule["cleanup-expired-idempotency-records"]["options"] == {
        "queue": "maintenance"
    }

    assert schedule["flush-expired-jwt-tokens"]["options"] == {"queue": "maintenance"}

    scheduled_tasks = {entry["task"] for entry in schedule.values()}

    assert scheduled_tasks == {
        "tournaments.tasks.maintenance.cleanup_expired_idempotency_records",
        "tournaments.tasks.maintenance.flush_expired_tokens",
    }


def test_gameplay_services_are_not_celery_routes():
    routed_tasks = set(settings.CELERY_TASK_ROUTES)

    forbidden_fragments = {
        "roll_dice",
        "hold_dice",
        "select_category",
        "ranking",
        "round_barrier",
    }

    assert not any(
        fragment in task_name
        for task_name in routed_tasks
        for fragment in forbidden_fragments
    )


def test_celery_runs_eagerly_without_a_real_broker():
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True
