from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
def test_pre_commit_runs_required_fast_quality_checks():
    config = (PROJECT_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    for hook_id in (
        "trailing-whitespace",
        "end-of-file-fixer",
        "check-yaml",
        "ruff-check",
        "ruff-format-check",
        "fast-unit-tests",
    ):
        assert f"id: {hook_id}" in config

    assert '"-m"' in config
    assert '"unit and not slow"' in config


@pytest.mark.unit
def test_ci_checks_migrations_postgresql_full_tests_and_coverage():
    workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "postgres:" in workflow
    assert "@postgres:5432" in workflow
    assert "POSTGRES_SERVICE_HOST: postgres" in workflow
    assert "makemigrations --check --dry-run" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run ruff format --check ." in workflow
    assert "uv run coverage run -m pytest" in workflow
    assert "uv run coverage report" in workflow
    assert "printenv" not in workflow
    assert "echo $SECRET_KEY" not in workflow
    assert "echo ${SECRET_KEY}" not in workflow

    completed_test = (
        "src/tournaments/tests/test_seed_demo.py::"
        "test_seed_demo_supports_each_mvp_scenario[completed]"
    )

    regular_step = workflow.split(
        "- name: Run regular test suite with coverage",
        1,
    )[1].split(
        "- name: Run completed demo scenario without coverage",
        1,
    )[0]

    regular_command = " ".join(regular_step.split())

    assert (
        f'uv run coverage run -m pytest --deselect="{completed_test}"'
    ) in regular_command

    assert '-m "not slow"' not in regular_step

    isolated_step = workflow.split(
        "- name: Run completed demo scenario without coverage",
        1,
    )[1].split(
        "- name: Report coverage",
        1,
    )[0]

    assert '-m "not slow"' not in regular_step
    assert f'--deselect="{completed_test}"' in regular_step
    assert "uv run pytest -q" in isolated_step
    assert f'"{completed_test}"' in isolated_step
    assert "--deselect" not in isolated_step


@pytest.mark.unit
def test_quality_configuration_declares_slow_marker_and_ignores_coverage_artifacts():
    pytest_config = (PROJECT_ROOT / "pytest.ini").read_text(encoding="utf-8")
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    coverage_config = (PROJECT_ROOT / ".coveragerc").read_text(encoding="utf-8")

    assert "--strict-markers" in pytest_config
    assert "slow:" in pytest_config
    assert ".coverage" in gitignore
    assert "htmlcov/" in gitignore
    assert "branch = True" in coverage_config
    assert "*/migrations/*" in coverage_config
