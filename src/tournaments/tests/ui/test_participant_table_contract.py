from pathlib import Path

import pytest


@pytest.mark.unit
def test_table_template_exposes_accessible_status_and_semantic_controls():
    template = Path("src/tournaments/templates/tournaments/table.html").read_text(
        encoding="utf-8"
    )

    assert 'aria-live="polite"' in template
    assert 'id="roll-button"' in template
    assert '<button id="roll-button"' in template
    assert 'id="category-help"' in template
    assert 'id="connection-status"' in template
    assert 'id="logout-button"' in template
    assert 'id="physical-roll"' in template
    assert 'id="physical-roll-form"' in template
    assert "Dice&nbsp;total" not in template
    assert ">Dice</h2>" not in template


@pytest.mark.unit
def test_table_template_keeps_internal_game_id_out_of_visible_heading():
    template = Path("src/tournaments/templates/tournaments/table.html").read_text(
        encoding="utf-8"
    )

    assert 'data-game-id="{{ game_id }}"' in template
    assert "Table {{ game_id }}" not in template
    assert "{{ table_label_ui }}" in template


@pytest.mark.unit
def test_table_javascript_sends_only_user_intentions():
    script = Path("src/tournaments/static/tournaments/js/table.js").read_text(
        encoding="utf-8"
    )

    assert "player_id" not in script
    assert '"points"' not in script
    assert "const rules" not in script
    assert 'error.code ?? "REQUEST_FAILED"' in script
    assert "item.information" in script
    assert "response.status === 403 || response.status === 409" in script
    assert "/api/auth/logout/" in script
    assert "logoutDialog.showModal()" in script
    assert "snapshot.participation_ongoing" in script
    assert "snapshot.game_complete" not in script
    assert "--participant-count" in script
    assert "th.title = participant.name" in script
    assert "snapshot.category_sections" in script
    assert "turn.can_hold" in script
    assert "turn?.selectable_category_ids?.includes(category.id)" in script
    assert 'snapshot.event_mode === "in_person"' in script
    assert "submitRoll({values})" in script
    assert "SNAPSHOT_POLL_MS = 1000" in script
    assert "window.setInterval(pollSnapshot, SNAPSHOT_POLL_MS)" in script
    assert 'window.addEventListener("focus", pollSnapshot)' in script

    assert "error.message" not in script.replace(
        'error.message === "RELOGIN_REQUIRED"',
        "",
    )


@pytest.mark.unit
def test_category_decision_is_rendered_only_in_participant_cell():
    script = Path("src/tournaments/static/tournaments/js/table.js").read_text(
        encoding="utf-8"
    )

    assert 'button.className = "score-action"' in script
    assert "beginCategoryChoice(category, button)" in script
    assert 'info.addEventListener("click", () => showHelp(category, info))' in script
    assert "labelText.textContent = shortLabel(category.label)" in script
    assert 'button.textContent = "Choose"' not in script
    assert 'category.id === "pair"' in script
    assert "payload.pair_value = pairValue" in script


@pytest.mark.unit
def test_api_javascript_shares_one_refresh_and_retries_once():
    script = Path("src/tournaments/static/tournaments/js/api.js").read_text(
        encoding="utf-8"
    )

    assert "let refreshPromise = null" in script
    assert "apiRequest(url, options, false)" in script
    assert 'throw new Error("RELOGIN_REQUIRED")' in script


@pytest.mark.unit
def test_participant_page_uses_the_same_drf_authentication_boundary():
    view = Path("src/tournaments/views.py").read_text(encoding="utf-8")

    assert "@login_required" not in view
    assert '@api_view(["GET"])' in view
    assert "@permission_classes([IsAuthenticated])" in view
    assert "request._request" in view


@pytest.mark.unit
def test_scorecard_css_supports_dynamic_player_columns_and_internal_grid():
    css = Path("src/tournaments/static/tournaments/css/table.css").read_text(
        encoding="utf-8"
    )

    assert "--participant-count" in css
    assert "table-layout: fixed" in css
    assert "white-space: pre-line" in css
    assert "min-width: 8.5rem" in css
    assert "text-overflow: ellipsis" in css
    assert "border-right-color: #c7ccc5" in css
