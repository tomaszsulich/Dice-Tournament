import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCUMENTATION_FILES = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "README.en.md",
    PROJECT_ROOT / "docs" / "architecture.md",
    PROJECT_ROOT / "docs" / "architecture.en.md",
    PROJECT_ROOT / "docs" / "api.md",
    PROJECT_ROOT / "docs" / "api.en.md",
    PROJECT_ROOT / "docs" / "security.md",
    PROJECT_ROOT / "docs" / "security.en.md",
    PROJECT_ROOT / "docs" / "decisions.md",
    PROJECT_ROOT / "docs" / "decisions.en.md",
    PROJECT_ROOT / "docs" / "plans" / "01_system_specification.md",
    PROJECT_ROOT / "docs" / "plans" / "01_system_specification.en.md",
    PROJECT_ROOT / "docs" / "plans" / "02_business_plan.md",
    PROJECT_ROOT / "docs" / "plans" / "02_business_plan.en.md",
    PROJECT_ROOT / "docs" / "plans" / "03_technical_plan.md",
    PROJECT_ROOT / "docs" / "plans" / "03_technical_plan.en.md",
)

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def _local_link_target(source: Path, raw_target: str) -> tuple[Path, str | None]:
    path_text, separator, anchor = raw_target.partition("#")
    target = source if not path_text else (source.parent / path_text).resolve()
    return target, anchor if separator else None


@pytest.mark.unit
def test_documentation_links_resolve_to_existing_files_and_explicit_anchors():
    for document in DOCUMENTATION_FILES:
        content = document.read_text(encoding="utf-8")

        for raw_target in MARKDOWN_LINK.findall(content):
            if raw_target.startswith(("http://", "https://", "mailto:")):
                continue

            target, anchor = _local_link_target(document, raw_target)
            assert target.is_file(), f"Broken link in {document}: {raw_target}"

            if anchor:
                target_content = target.read_text(encoding="utf-8")

                assert f'id="{anchor}"' in target_content, (
                    f"Missing explicit anchor in {target}: {anchor}"
                )


@pytest.mark.unit
def test_language_switch_links_only_to_the_other_language():
    for document in DOCUMENTATION_FILES:
        content = document.read_text(encoding="utf-8")
        first_line = content.splitlines()[0]

        if document.name.endswith(".en.md"):
            assert first_line.startswith("[Polski](")
            assert first_line.endswith("| English")
            assert "[English]" not in first_line
        else:
            assert first_line.startswith("Polski |")
            assert "[English](" in first_line
            assert "[Polski]" not in first_line

        assert "#document-top" not in first_line
        assert "#readme-top" not in first_line


@pytest.mark.unit
def test_readmes_document_repository_root_commands_and_daphne_src_exception():
    for readme_name in ("README.md", "README.en.md"):
        content = (PROJECT_ROOT / readme_name).read_text(encoding="utf-8")

        for required_command in (
            "python -m pip install uv==0.12.15",
            "uv sync --frozen",
            "python src/manage.py migrate",
            "Set-Location src",
            "daphne -b 127.0.0.1 -p 8000 config.asgi:application",
            "docker compose up --build",
            "pytest",
            "python -m ruff check .",
            "python -m ruff format --check .",
        ):
            assert required_command in content

        assert "REDIS_HOST_PORT" in content
        assert "WEB_HOST_PORT" in content


@pytest.mark.unit
def test_locked_dependencies_are_used_in_local_docker_and_ci_workflows():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert (PROJECT_ROOT / "uv.lock").is_file()
    assert 'requires-python = ">=3.12,<3.13"' in pyproject
    assert "uv sync --frozen --no-dev" in dockerfile
    assert "uv sync --frozen" in workflow
    assert "uv run coverage run -m pytest" in workflow

    obsolete_paths = (
        "requirements/base.txt",
        "requirements/dev.txt",
        "docs/01_system_specification.md",
        "docs/02_business_plan.md",
        "docs/03_technical_plan.md",
        "src/accounts/tests/factories.py",
        "src/tournaments/tests/demo_builders/__init__.py",
    )

    for path in obsolete_paths:
        assert not (PROJECT_ROOT / path).exists()


@pytest.mark.unit
def test_unsuffixed_documents_are_polish_and_english_uses_en_suffix():
    assert not list(PROJECT_ROOT.rglob("*.pl.md"))

    for polish_document in DOCUMENTATION_FILES[::2]:
        english_document = polish_document.with_name(
            f"{polish_document.stem}.en{polish_document.suffix}"
        )

        assert english_document in DOCUMENTATION_FILES
