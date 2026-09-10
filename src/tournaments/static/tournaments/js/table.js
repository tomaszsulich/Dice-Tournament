import { apiRequest } from "./api.js";

const root = document.querySelector(".table-layout");
const gameId = root.dataset.gameId;

const initialSnapshot = document.getElementById("initial-game-snapshot");
const helpPopover = document.getElementById("category-help");
const pairDialog = document.getElementById("pair-choice");
const physicalRollDialog = document.getElementById("physical-roll");
const physicalRollForm = document.getElementById("physical-roll-form");
const logoutDialog = document.getElementById("logout-confirm");

const narrowScreen = window.matchMedia("(max-width: 47.99rem)");
const dieFaces = ["—", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];

let snapshot = JSON.parse(initialSnapshot.textContent);
let pending = false;
let activeHelpAnchor = null;
let snapshotPollInFlight = false;
const SNAPSHOT_POLL_MS = 1000;

function idempotencyKey() {
    return crypto.randomUUID();
}

function shortLabel(text) {
    const words = text.trim().split(/\s+/);
    return words.length === 2 ? words.join("\u00a0") : text;
}

export function render(next) {
    snapshot = next;
    const turn = snapshot.turn;
    const rollButton = document.getElementById("roll-button");
    const canRoll = Boolean(turn?.can_roll && !pending);

    root.setAttribute("aria-busy", String(pending));
    rollButton.textContent = turn?.roll_count ? "Roll\u00a0again" : "Roll";
    rollButton.disabled = !canRoll;

    document.getElementById("turn-status").textContent = turn
        ? turn.is_current_user
            ? turn.category_required
                ? "Choose a\u00a0category"
                : "Your\u00a0turn"
            : "Another participant's\u00a0turn"
        : "Table\u00a0finished";

    document.getElementById("rerolls-remaining").textContent =
        turn?.rerolls_remaining ?? "—";

    renderDice(turn);
    renderScorecard(turn);
}

function renderDice(turn) {
    const normal = document.getElementById("dice");
    const held = document.getElementById("held-dice");

    normal.replaceChildren();
    held.replaceChildren();

    (turn?.dice ?? []).forEach((value, index) => {
        const button = document.createElement("button");
        const isHeld = Boolean(turn.held_dice[index]);

        button.type = "button";
        button.className = `die${value == null ? " is-empty" : ""}`;
        button.textContent = value == null ? "—" : dieFaces[value];
        button.dataset.index = index;

        button.setAttribute(
            "aria-label",
            value == null
                ? `Die ${index + 1}, not rolled yet`
                : `Die ${index + 1}, value ${value}${isHeld ? ", held" : ""}`,
        );

        button.setAttribute("aria-pressed", String(isHeld));

        button.disabled = pending || !turn.can_hold;

        button.addEventListener("click", () => toggleHold(index));

        (isHeld ? held : normal).append(button);
    });
}

function renderScorecard(turn) {
    const head = document.getElementById("scorecard-head");
    const categoryHeading = document.createElement("th");
    categoryHeading.scope = "col";
    categoryHeading.textContent = "Category";
    head.replaceChildren(categoryHeading);

    root.style.setProperty("--participant-count", snapshot.participants.length);

    snapshot.participants.forEach((participant) => {
        const th = document.createElement("th");
        th.scope = "col";
        th.className = "participant-heading";
        th.textContent = participant.name;
        th.title = participant.name;
        head.append(th);
    });

    const body = document.getElementById("scorecard-body");
    body.replaceChildren();

    appendSectionRow(body, "school");

    snapshot.categories.forEach((category, index) => {
        if (index === 6) appendSectionRow(body, "figures");
        body.append(buildCategoryRow(category, turn));
    });

    renderTotalRow(body);
}

function appendSectionRow(body, sectionId) {
    const section = snapshot.category_sections?.[sectionId];
    if (!section) return;

    const row = document.createElement("tr");
    const cell = document.createElement("th");
    const label = document.createElement("span");
    const info = document.createElement("button");

    row.className = "section-row";
    cell.colSpan = snapshot.participants.length + 1;
    cell.scope = "colgroup";
    label.textContent = section.label;

    info.type = "button";
    info.className = "section-info-button";
    info.textContent = "i";
    info.setAttribute("aria-label", `Information about ${section.label}`);
    info.addEventListener("click", () => showHelp(section, info));

    cell.append(label, info);
    row.append(cell);
    body.append(row);
}

function buildCategoryRow(category, turn) {
    const row = document.createElement("tr");
    const label = document.createElement("th");
    const labelText = document.createElement("span");
    const info = document.createElement("button");

    label.scope = "row";
    label.className = "category-cell";
    labelText.className = "category-label";
    labelText.textContent = shortLabel(category.label);

    info.type = "button";
    info.className = "info-button";
    info.textContent = "i";
    info.setAttribute("aria-label", `Information about ${category.label}`);
    info.addEventListener("click", () => showHelp(category, info));

    label.append(labelText, info);
    row.append(label);

    snapshot.participants.forEach((participant) => {
        const cell = document.createElement("td");
        const value = participant.scores[category.id];

        const canChoose =
            participant.is_current_user &&
            participant.is_active &&
            Boolean(turn?.selectable_category_ids?.includes(category.id)) &&
            !pending;

        cell.className = "score-cell";

        if (canChoose) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "score-action";
            button.setAttribute("aria-label", `Choose ${category.label}`);
            button.title = `Choose ${category.label}`;
            button.addEventListener("click", () => beginCategoryChoice(category, button));
            cell.append(button);
        } else {
            cell.textContent = value ?? "—";
        }

        row.append(cell);
    });

    return row;
}

function renderTotalRow(body) {
    const row = document.createElement("tr");
    const heading = document.createElement("th");

    row.className = "total-row";
    heading.scope = "row";
    heading.textContent = "Total";
    row.append(heading);

    snapshot.participants.forEach((participant) => {
        const cell = document.createElement("td");
        cell.textContent = participant.total_score;
        row.append(cell);
    });

    body.append(row);
}

function beginCategoryChoice(category, anchor) {
    const options = category.selection_options ?? [];

    if (category.id === "pair" && options.length > 1) {
        showPairChoice(options, anchor);
        return;
    }

    chooseCategory(category.id);
}

function showPairChoice(options, anchor) {
    const container = document.getElementById("pair-choice-options");
    container.replaceChildren();

    options.forEach((value) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = `Pair of ${value}s`;

        button.addEventListener("click", () => {
            pairDialog.close();
            chooseCategory("pair", value);
        });

        container.append(button);
    });

    openChoiceDialog(pairDialog, anchor);
}

async function command(path, options) {
    if (pending) return;

    pending = true;
    render(snapshot);
    setStatus("Saving…", "");

    try {
        const response = await apiRequest(path, options);

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));

            if (response.status === 403 || response.status === 409) {
                await reloadSnapshot();
            }

            throw new Error(error.code ?? "REQUEST_FAILED");
        }

        await reloadSnapshot();
        setStatus("", "");
    } catch (error) {

        if (error.message === "RELOGIN_REQUIRED") {
            setStatus("", "Session expired. Sign in again.");
        } else {
            setStatus("", "Action failed. Latest state restored.");
        }

    } finally {
        pending = false;
        render(snapshot);
    }
}

async function reloadSnapshot() {
    const response = await apiRequest(`/api/games/${gameId}/state/`);
    if (response.ok) snapshot = await response.json();
}

function roll() {
    if (snapshot.event_mode === "in_person") {
        showPhysicalRoll();
        return;
    }

    submitRoll({});
}

function submitRoll(payload) {
    command(`/api/games/${gameId}/roll/`, {
        method: "POST",
        headers: {"Idempotency-Key": idempotencyKey()},
        body: JSON.stringify(payload),
    });
}

function showPhysicalRoll() {
    const container = document.getElementById("physical-roll-values");
    container.replaceChildren();

    snapshot.turn.dice.forEach((value, index) => {
        const label = document.createElement("label");
        const input = document.createElement("input");
        const held = Boolean(snapshot.turn.held_dice[index]);

        label.textContent = `Die ${index + 1}`;
        input.type = "number";
        input.name = `die-${index + 1}`;
        input.min = "1";
        input.max = "6";
        input.step = "1";
        input.required = true;
        input.inputMode = "numeric";

        if (held) {
            input.value = String(value);
            input.readOnly = true;
        }

        label.append(input);
        container.append(label);
    });

    physicalRollDialog.showModal();
}

function toggleHold(index) {
    const held = [...snapshot.turn.held_dice];
    held[index] = !held[index];

    command(`/api/games/${gameId}/holds/`, {
        method: "POST",
        body: JSON.stringify({held}),
    });
}

function chooseCategory(category, pairValue = null) {
    const payload = {category};
    if (pairValue !== null) payload.pair_value = pairValue;

    command(`/api/games/${gameId}/choose-category/`, {
        method: "POST",
        headers: {"Idempotency-Key": idempotencyKey()},
        body: JSON.stringify(payload),
    });
}

function showHelp(item, anchor) {
    if (!helpPopover.hidden && activeHelpAnchor === anchor) {
        closeHelp();
        return;
    }

    document.getElementById("help-title").textContent = shortLabel(item.label);

    document.getElementById("help-text").textContent =
        item.information ?? "No extra rule information.";

    activeHelpAnchor = anchor;
    helpPopover.hidden = false;
    positionPopover(helpPopover, anchor);
}

function closeHelp() {
    helpPopover.hidden = true;
    activeHelpAnchor = null;
}

function positionPopover(popover, anchor) {
    if (narrowScreen.matches) {
        popover.style.removeProperty("left");
        popover.style.removeProperty("top");
        return;
    }

    const rect = anchor.getBoundingClientRect();
    const width = popover.getBoundingClientRect().width;
    const height = popover.getBoundingClientRect().height;
    const left = Math.min(window.innerWidth - width - 12, Math.max(12, rect.right - width));
    const top = Math.min(window.innerHeight - height - 12, rect.bottom + 7);

    popover.style.left = `${left}px`;
    popover.style.top = `${Math.max(12, top)}px`;
}

function openChoiceDialog(dialog, anchor) {
    if (dialog.open) dialog.close();

    if (narrowScreen.matches) {
        dialog.style.removeProperty("left");
        dialog.style.removeProperty("top");
        dialog.showModal();
        return;
    }

    dialog.show();
    const rect = anchor.getBoundingClientRect();
    const width = dialog.getBoundingClientRect().width;

    const left = Math.min(window.innerWidth - width - 12, Math.max(12, rect.right - width));
    const top = Math.min(window.innerHeight - dialog.offsetHeight - 12, rect.bottom + 8);

    dialog.style.position = "fixed";
    dialog.style.left = `${left}px`;
    dialog.style.top = `${Math.max(12, top)}px`;
}

function requestLogout() {
    if (!snapshot.participation_ongoing) {
        performLogout();
        return;
    }

    logoutDialog.showModal();
    document.getElementById("logout-stay").focus();
}

async function performLogout() {
    const button = document.getElementById("logout-button");
    const confirmButton = document.getElementById("logout-confirm-button");
    button.disabled = true;
    confirmButton.disabled = true;

    try {
        const response = await apiRequest("/api/auth/logout/", {method: "POST"});

        if (!response.ok) throw new Error("LOGOUT_FAILED");
        window.location.assign("/login/");
    } catch {

        if (logoutDialog.open) logoutDialog.close();
        button.disabled = false;
        confirmButton.disabled = false;
        setStatus("", "Sign out failed. Try again.");
    }
}

function setStatus(status, error) {
    document.getElementById("request-status").textContent = status;
    document.getElementById("error-message").textContent = error;
}

document.getElementById("roll-button").addEventListener("click", roll);
physicalRollForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!physicalRollForm.reportValidity()) return;

    const values = [...document.querySelectorAll("#physical-roll-values input")].map(
        (input) => Number(input.value),
    );
    physicalRollDialog.close();
    submitRoll({values});
});
document.getElementById("physical-roll-close").addEventListener("click", () => physicalRollDialog.close());
document.getElementById("logout-button").addEventListener("click", requestLogout);
document.getElementById("logout-stay").addEventListener("click", () => logoutDialog.close());
document.getElementById("logout-confirm-button").addEventListener("click", performLogout);
document.getElementById("help-close").addEventListener("click", closeHelp);
document.getElementById("pair-choice-close").addEventListener("click", () => pairDialog.close());

document.addEventListener("click", (event) => {
    if (helpPopover.hidden) return;
    if (helpPopover.contains(event.target) || activeHelpAnchor?.contains(event.target)) return;
    closeHelp();
});

window.addEventListener("resize", () => {
    if (!helpPopover.hidden && activeHelpAnchor) positionPopover(helpPopover, activeHelpAnchor);
});

async function pollSnapshot() {
    if (document.hidden || pending || snapshotPollInFlight) return;

    snapshotPollInFlight = true;
    try {
        const response = await apiRequest(`/api/games/${gameId}/state/`);
        if (response.ok) render(await response.json());
    } finally {
        snapshotPollInFlight = false;
    }
}

window.setInterval(pollSnapshot, SNAPSHOT_POLL_MS);
document.addEventListener("visibilitychange", () => {
    if (!document.hidden) pollSnapshot();
});
window.addEventListener("focus", pollSnapshot);

render(snapshot);
