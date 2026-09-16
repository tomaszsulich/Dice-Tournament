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
def test_completed_dashboard_navigates_from_participant_picker_to_comparison():
    template = (
        Path(settings.BASE_DIR)
        / "tournaments/templates/tournaments/organizer_dashboard.html"
    ).read_text(encoding="utf-8")

    source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/organizer_dashboard.js"
    ).read_text(encoding="utf-8")

    assert "initial_dashboard.comparison_participants" in template
    assert 'id="comparison-participant"' in template
    assert "participant.display_name" in template
    assert "participant.nickname" in template
    assert 'aria-label="Participant"' in template
    assert "Choose participant" not in template
    assert "comparison-navigation" in source

    assert (
        "`/comparisons/participants/${profileId}/?tournament_id=${tournamentId}`"
        in source
    )

    assert '["Round", table.round.name || `Round ${table.round.number}`]' in source


@pytest.mark.unit
def test_comparison_results_are_at_most_two_columns_and_use_one_modal():
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

    options_rule = css.split(".comparison-picker__options {", 1)[1].split("}", 1)[0]
    results_rule = css.split(".comparison-grid {", 1)[1].split("}", 1)[0]

    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in options_rule
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in results_rule
    assert "repeat(3" not in css
    assert "@media (max-width: 1100px)" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert ".comparison-picker__options { grid-template-columns: 1fr; }" in css

    summary_rule = css.split(".summary {", 1)[1].split("}", 1)[0]
    attention_rule = css.split(".attention {", 1)[1].split("}", 1)[0]

    assert "position: sticky" not in summary_rule
    assert "position: sticky" in attention_rule
    assert ".comparison-picker > button" in css
    assert "margin-left: auto" in css

    option_name_rule = css.split(".comparison-picker__options label span {", 1)[
        1
    ].split("}", 1)[0]

    assert "min-width: 0" in option_name_rule
    assert "overflow-wrap: anywhere" in option_name_rule
    assert "max-content" not in options_rule

    fieldset_rule = css.split(".comparison-picker fieldset {", 1)[1].split("}", 1)[0]

    assert "min-width: 0" in fieldset_rule
    assert "max-width: 100%" in fieldset_rule
    assert "min-width: 0" in options_rule
    assert "max-width: 100%" in options_rule


@pytest.mark.unit
def test_comparison_names_keep_segments_with_separator_and_break_before_sequence():
    source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/participant_comparison.js"
    ).read_text(encoding="utf-8")

    assert 'const parts = name.split(" | ")' in source
    assert "` |\\u00a0${part}`" in source
    assert "/^#\\d+$/.test(part)" in source
    assert 'document.createTextNode("\\u00a0|")' in source
    assert 'document.createElement("wbr")' in source
    assert '["16", "64", "128"]' not in source


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
def test_dashboard_tournament_context_opens_comparison_without_second_selection():
    source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/participant_comparison.js"
    ).read_text(encoding="utf-8")

    template = (
        Path(settings.BASE_DIR)
        / "tournaments/templates/tournaments/participant_comparison.html"
    ).read_text(encoding="utf-8")

    assert "data-initial-tournament-id" in template
    assert "tournament.id == initial_tournament_id" in template
    assert "root.dataset.initialTournamentId" in source
    assert "comparisonForm.requestSubmit()" in source
    assert "comparisonForm.hidden" not in source


@pytest.mark.unit
def test_history_modal_closes_from_the_backdrop_without_blocking_its_content():
    source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/participant_comparison.js"
    ).read_text(encoding="utf-8")

    assert 'modal.addEventListener("click"' in source
    assert "event.target === modal" in source
    assert "modal.close()" in source


@pytest.mark.unit
def test_names_and_roll_history_keep_the_required_frontend_contracts():
    organizer_source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/organizer_dashboard.js"
    ).read_text(encoding="utf-8")

    comparison_source = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/js/participant_comparison.js"
    ).read_text(encoding="utf-8")

    css = (
        Path(settings.BASE_DIR)
        / "tournaments/static/tournaments/css/organizer_dashboard.css"
    ).read_text(encoding="utf-8")

    assert 'button.querySelector(".participant").textContent' in organizer_source
    assert 'span.className = "person-name"' in organizer_source
    assert 'span.className = "person-name"' in comparison_source
    assert ".person-name" in css
    assert "white-space: nowrap" in css

    assert "held_after_roll" in comparison_source
    assert "roll.decision" in comparison_source
    assert "roll.decision.selected_at" in comparison_source
    assert "first_roll_bonus_applied" in comparison_source
    assert 'return "no dice"' in comparison_source
    assert "die in position" in comparison_source
    assert "dice in positions" in comparison_source
    assert '"Held after roll: not applicable"' in comparison_source

    assert (
        'empty.textContent = "No roll history was recorded for this tournament."'
        in comparison_source
    )

    assert "loadHistory(historyPage + 1, true)" in comparison_source
    assert 'params.set("round_id", String(historyRoundId))' in comparison_source
    assert "timeZone: historyTimeZone" in comparison_source

    assert 'id="history-round"' in (
        Path(settings.BASE_DIR)
        / "tournaments/templates/tournaments/participant_comparison.html"
    ).read_text(encoding="utf-8")

    assert "#history-more[hidden]" in css
    assert "max-height: min(58vh, 30rem)" in css
    assert "overflow-y: auto" in css
