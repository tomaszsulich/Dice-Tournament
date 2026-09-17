import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
def test_compose_config_renders():
    docker = shutil.which("docker")

    if docker is None:
        pytest.skip("Docker CLI is not available.")

    env = os.environ.copy()

    env.update(
        {
            "SECRET_KEY": "compose-test-secret",
            "POSTGRES_DB": "dice_tournament",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "compose-test-password",
        }
    )

    result = subprocess.run(
        [docker, "compose", "config", "--quiet"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
    )

    unavailable_messages = (
        "is not a docker command",
        'unknown command "compose"',
    )

    if result.returncode != 0 and any(
        message in result.stderr.lower() for message in unavailable_messages
    ):
        pytest.skip("Docker Compose plugin is not available.")

    assert result.returncode == 0, result.stderr


@pytest.mark.integration
@pytest.mark.slow
def test_compose_runtime_smoke_is_healthy_when_explicitly_enabled():
    if os.getenv("RUN_COMPOSE_SMOKE") != "1":
        pytest.skip("Set RUN_COMPOSE_SMOKE=1 to run the isolated Compose smoke test.")

    docker = shutil.which("docker")

    if docker is None:
        pytest.fail("RUN_COMPOSE_SMOKE=1 requires the Docker CLI.")

    env = os.environ.copy()

    env.update(
        {
            "COMPOSE_PROJECT_NAME": f"dice-tournament-smoke-{os.getpid()}",
            "SECRET_KEY": "compose-smoke-local-only",
            "POSTGRES_DB": "dice_tournament_smoke",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "compose-smoke-password",
            "ALLOWED_HOSTS": "localhost,127.0.0.1",
            # Let Docker choose free host ports so the smoke test can run
            # alongside an already running development stack.
            "WEB_HOST_PORT": "0",
            "REDIS_HOST_PORT": "0",
        }
    )

    services = [
        "db",
        "redis",
        "web",
        "celery-notifications",
        "celery-maintenance",
        "celery-beat",
    ]

    def collect_compose_diagnostics() -> str:
        commands = (
            [docker, "compose", "ps", "--all"],
            [docker, "compose", "logs", "--no-color", "--tail=80"],
        )

        sections = []

        for command in commands:
            result = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                env=env,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=30,
            )

            sections.append(
                f"$ {' '.join(command[1:])}\n{result.stdout}\n{result.stderr}".strip()
            )

        return "\n\n".join(sections)

    try:
        up = subprocess.run(
            [docker, "compose", "up", "-d", "--wait", *services],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=240,
        )

        if up.returncode != 0:
            pytest.fail(f"{up.stderr}\n\n{collect_compose_diagnostics()}")

        ps = subprocess.run(
            [docker, "compose", "ps"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=30,
        )

        assert ps.returncode == 0, ps.stderr
        assert "unhealthy" not in ps.stdout.lower(), collect_compose_diagnostics()
        assert "exited" not in ps.stdout.lower(), collect_compose_diagnostics()

    finally:
        subprocess.run(
            [docker, "compose", "down", "-v", "--remove-orphans"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=120,
        )
