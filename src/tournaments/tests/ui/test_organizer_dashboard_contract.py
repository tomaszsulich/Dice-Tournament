from pathlib import Path

import pytest
from django.conf import settings


@pytest.mark.unit
def test_realtime_updates_one_card_and_reuses_one_detail_panel():
    source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/organizer_dashboard.js"
    ).read_text(encoding="utf-8")

    assert "existing.replaceWith(tableCard(table))" in source
    assert 'message.type === "table_changed"' in source
    assert "refresh(message.table_id)" in source
    assert "showDetail" in source
    assert "frontend" not in source.lower()
    assert 'event.target.closest(".table-card, .attention-item")' in source
    assert 'event.key !== "Escape"' in source
    assert 'status.textContent = "Connected"' in source
    assert "if (counter)" in source
    assert 'link.textContent = "Sign\\u00a0in again"' in source
    assert "/login/?next=" in source
    assert "encodeURIComponent(returnTo)" in source


@pytest.mark.unit
def test_comparison_layout_is_at_most_two_columns_and_uses_one_modal():
    template = (
        Path(settings.BASE_DIR)
        / "tournaments/templates/tournaments/participant_comparison.html"
    ).read_text(encoding="utf-8")

    css = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/css/organizer_dashboard.css"
    ).read_text(encoding="utf-8")

    assert template.count("<dialog") == 1
    assert template.count('id="history-modal"') == 1
    assert "grid-template-columns: repeat(2" in css
    assert "repeat(3" not in css

    summary_rule = css.split(".summary {", 1)[1].split("}", 1)[0]
    attention_rule = css.split(".attention {", 1)[1].split("}", 1)[0]

    assert "position: sticky" not in summary_rule
    assert "position: sticky" in attention_rule
    assert ".comparison-picker > button" in css
    assert "margin-left: auto" in css


@pytest.mark.unit
def test_frontend_sends_only_ids_and_never_calculates_ranking():
    source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/participant_comparison.js"
    ).read_text(encoding="utf-8")

    assert 'params.append("tournament_ids", input.value)' in source
    assert "raw_score" not in source
    assert "sort(" not in source
    assert "rank" not in source.lower()


@pytest.mark.unit
def test_history_modal_closes_from_the_backdrop_without_blocking_its_content():
    source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/participant_comparison.js"
    ).read_text(encoding="utf-8")

    assert 'modal.addEventListener("click"' in source
    assert "event.target === modal" in source
    assert "modal.close()" in source
