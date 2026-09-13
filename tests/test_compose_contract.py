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
