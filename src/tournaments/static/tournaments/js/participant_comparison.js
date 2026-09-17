import { apiRequest } from "./api.js";

const root = document.querySelector(".comparison");
const participantId = root.dataset.participantId;
const modal = document.getElementById("history-modal");
const historyRound = document.getElementById("history-round");
let historyTournamentId = null;
let historyRoundId = null;
let historyTimeZone = "UTC";
let historyPage = 1;

function appendTournamentName(element, name) {
    const parts = name.split(" | ");
    element.append(document.createTextNode(parts.shift() ?? ""));

    parts.forEach((part) => {
        if (/^#\d+$/.test(part)) {
            element.append(document.createTextNode("\u00a0|"));
            element.append(document.createElement("wbr"));
            element.append(document.createTextNode(` ${part}`));
            return;
        }

        element.append(document.createTextNode(` |\u00a0${part}`));
    });
}

function personName(name) {
    const span = document.createElement("span");
    span.className = "person-name";
    span.textContent = name;
    return span;
}

function summaryRow(item) {
    const row = document.createElement("tr");
    const tournament = document.createElement("td");
    appendTournamentName(tournament, item.tournament.name);
    row.append(tournament);

    [
        item.total,
        item.round_average.toFixed(2),
        item.best_round ?? "—",
        item.rounds_played,
    ].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
    });
    return row;
}

function detailCard(item) {
    const article = document.createElement("details");
    article.className = "comparison-card";
    article.open = true;

    const summary = document.createElement("summary");
    const heading = document.createElement("h2");
    const identity = document.createElement("p");
    const rounds = document.createElement("ol");
    const history = document.createElement("button");

    appendTournamentName(heading, item.tournament.name);
    identity.append(
        document.createTextNode("Historical\u00a0name: "),
        personName(item.participant_snapshot.display_name),
    );

    item.rounds.forEach((round) => {
        const row = document.createElement("li");
        row.textContent = `${round.round_name || `Round ${round.round_number}`} · Table ${round.table_number} · ${round.score} points`;
        rounds.append(row);
    });

    history.type = "button";
    history.textContent = "Roll\u00a0history";
    history.addEventListener("click", () => openHistory(item));

    summary.append(heading);
    article.append(summary, identity, rounds, history);
    return article;
}

function ownHistoryCard(item) {
    const article = document.createElement("article");
    const heading = document.createElement("h2");
    const history = document.createElement("button");

    article.className = "comparison-card";
    appendTournamentName(heading, item.tournament.name);
    history.type = "button";
    history.textContent = "Open roll\u00a0history";
    history.addEventListener("click", () => openHistory(item));
    article.append(heading, history);
    return article;
}

function decisionResult(decision) {
    if (decision.result_kind === "strike_off") return "X (strike-off)";

    if (decision.result_kind === "school_balance") {
        const prefix = decision.value > 0 ? "+" : "";
        return `${prefix}${decision.value} school balance`;
    }

    return `${decision.value} points`;
}

function formatHistoryTimestamp(value) {
    return new Date(value).toLocaleString(undefined, {
        dateStyle: "short",
        timeStyle: "medium",
        timeZone: historyTimeZone,
    });
}

function heldDiceDescription(flags) {
    const positions = flags
        .map((isHeld, index) => (isHeld ? index + 1 : null))
        .filter((position) => position !== null);

    if (!positions.length) {
        return "no dice";
    }

    if (positions.length === 1) {
        return `die in position ${positions[0]}`;
    }

    return `dice in positions ${positions.join(", ")}`;
}

function historyItem(roll) {
    const item = document.createElement("article");
    const heading = document.createElement("h3");
    const meta = document.createElement("p");
    const dice = document.createElement("div");
    const heldForRoll = document.createElement("p");
    const holds = document.createElement("p");

    item.className = "history-item";
    heading.textContent = `Round ${roll.round_number} · Table ${roll.table_number} · Turn ${roll.turn_number} · Roll ${roll.roll_number}`;
    meta.className = "history-item__meta";
    meta.textContent = formatHistoryTimestamp(roll.rolled_at);
    dice.className = "history-dice";

    roll.dice.forEach((value, index) => {
        const die = document.createElement("span");
        die.className = "history-die";
        die.textContent = value;

        if (roll.held_after_roll?.[index]) {
            die.classList.add("history-die--held");
            die.title = "Held for the next roll";
        }

        dice.append(die);
    });

    heldForRoll.textContent = `Held for this roll: ${heldDiceDescription(roll.held_for_roll)}`;

    if (roll.held_after_roll === null) {
        holds.textContent = "Held after roll: not applicable";
    } else {
        holds.textContent = `Held after roll: ${heldDiceDescription(roll.held_after_roll)}`;
    }

    item.append(heading, meta, dice, heldForRoll, holds);

    if (roll.decision) {
        const decision = document.createElement("div");
        const category = document.createElement("strong");
        const result = document.createElement("span");
        const selectedAt = document.createElement("span");

        decision.className = "history-decision";
        category.textContent = `Category: ${roll.decision.category_label}`;
        result.textContent = `Result: ${decisionResult(roll.decision)}`;
        selectedAt.textContent = `Selected: ${formatHistoryTimestamp(roll.decision.selected_at)}`;
        decision.append(category, result, selectedAt);

        if (roll.decision.first_roll_bonus_applied) {
            const bonus = document.createElement("span");
            bonus.textContent = "First-roll ×2 bonus applied";
            decision.append(bonus);
        }

        item.append(decision);
    }

    return item;
}

function configureHistoryRounds(rounds) {
    const seen = new Set();
    const options = [new Option("All rounds", "")];

    rounds.forEach((round) => {
        if (seen.has(round.round_id)) return;
        seen.add(round.round_id);
        options.push(
            new Option(
                round.round_name || `Round ${round.round_number}`,
                String(round.round_id),
            ),
        );
    });

    historyRound.replaceChildren(...options);
    historyRound.value = "";
    historyRound.disabled = seen.size <= 1;
}

async function submitComparison(event) {
    event.preventDefault();
    const selected = [...document.querySelectorAll('input[name="tournament_ids"]:checked')];
    const error = document.getElementById("comparison-error");

    if (selected.length < 1 || selected.length > 4) {
        error.textContent = "Select between one and\u00a0four tournaments.";
        return;
    }

    error.textContent = "";
    const params = new URLSearchParams();
    selected.forEach((input) => params.append("tournament_ids", input.value));
    const response = await apiRequest(`/api/comparisons/participants/${participantId}/?${params}`);

    if (!response.ok) {
        error.textContent = "The\u00a0comparison is unavailable for the\u00a0selected tournaments.";
        return;
    }

    const result = await response.json();

    document.getElementById("comparison-summary-body").replaceChildren(
        ...result.comparisons.map(summaryRow),
    );

    document.getElementById("comparison-grid").replaceChildren(
        ...result.comparisons.map(detailCard),
    );

    document.getElementById("comparison-results").hidden = false;
}

async function loadHistory(pageNumber, append = false) {
    const more = document.getElementById("history-more");
    more.disabled = true;

    try {
        const params = new URLSearchParams({
            tournament_id: String(historyTournamentId),
            page: String(pageNumber),
        });

        if (historyRoundId !== null) {
            params.set("round_id", String(historyRoundId));
        }

        const response = await apiRequest(
            `/api/comparisons/participants/${participantId}/history/?${params}`,
        );

        if (!response.ok) return false;

        const result = await response.json();
        const content = document.getElementById("history-content");
        const rows = result.items.map(historyItem);

        if (append) {
            content.append(...rows);
        } else if (rows.length) {
            content.replaceChildren(...rows);
        } else {
            const empty = document.createElement("p");
            empty.className = "history-empty";
            if (historyRoundId === null) {
                empty.textContent = "No roll history was recorded for this tournament.";
            } else {
                empty.textContent = "No roll history was recorded for this round.";
            }
            content.replaceChildren(empty);
        }

        historyPage = result.pagination.page;
        more.hidden = !result.pagination.has_next;
        return true;
    } finally {
        more.disabled = false;
    }
}

async function openHistory(item) {
    historyTournamentId = item.tournament.id;
    historyRoundId = null;
    historyTimeZone = item.tournament.timezone;
    historyPage = 1;
    configureHistoryRounds(item.rounds);
    const title = document.getElementById("history-title");
    title.replaceChildren();
    appendTournamentName(title, item.tournament.name);
    title.append(document.createTextNode("\u00a0— roll\u00a0history"));
    await loadHistory(1);
    modal.showModal();
}

const comparisonForm = document.getElementById("comparison-form");

if (comparisonForm) {
    document
        .querySelectorAll(".comparison-picker__options label span")
        .forEach((name) => {
            const value = name.textContent;
            name.replaceChildren();
            appendTournamentName(name, value);
        });

    comparisonForm.addEventListener("submit", submitComparison);

    if (root.dataset.initialTournamentId) {
        comparisonForm.requestSubmit();
    }
}

const ownHistoryData = document.getElementById("own-history-data");

if (ownHistoryData) {
    const tournaments = JSON.parse(ownHistoryData.textContent);
    const grid = document.getElementById("own-history-grid");

    if (tournaments.length) {
        grid.replaceChildren(...tournaments.map(ownHistoryCard));
    } else {
        const empty = document.createElement("p");
        empty.className = "history-empty";
        empty.textContent = "No completed tournament roll history yet.";
        grid.replaceChildren(empty);
    }
}
document.getElementById("history-close").addEventListener("click", () => modal.close());

modal.addEventListener("click", (event) => {
    if (event.target === modal) modal.close();
});

historyRound.addEventListener("change", async () => {
    historyRoundId = historyRound.value ? Number(historyRound.value) : null;
    historyPage = 1;
    await loadHistory(1);
});

document.getElementById("history-more").addEventListener("click", async () => {
    await loadHistory(historyPage + 1, true);
});
