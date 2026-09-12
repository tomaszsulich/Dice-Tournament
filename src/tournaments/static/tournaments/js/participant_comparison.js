import { apiRequest } from "./api.js";

const root = document.querySelector(".comparison");
const participantId = root.dataset.participantId;
const modal = document.getElementById("history-modal");
let historyTournamentId = null;
let historyPage = 1;

function summaryRow(item) {
    const row = document.createElement("tr");
    [
        item.tournament.name,
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
    heading.textContent = item.tournament.name;
    identity.textContent = `Historical\u00a0name: ${item.participant_snapshot.display_name}`;

    item.rounds.forEach((round) => {
        const row = document.createElement("li");
        row.textContent = `${round.round_name || `Round ${round.round_number}`} · Table ${round.table_number} · ${round.score} points`;
        rounds.append(row);
    });

    history.type = "button";
    history.textContent = "Roll\u00a0history";
    history.addEventListener("click", () => openHistory(item.tournament.id, item.tournament.name));

    summary.append(heading);
    article.append(summary, identity, rounds, history);
    return article;
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

async function loadHistory(append = false) {
    const response = await apiRequest(
        `/api/comparisons/participants/${participantId}/history/?tournament_id=${historyTournamentId}&page=${historyPage}`,
    );

    if (!response.ok) return;
    const result = await response.json();
    const content = document.getElementById("history-content");

    const rows = result.items.map((roll) => {
        const item = document.createElement("article");
        item.className = "history-item";
        item.textContent = `Round ${roll.round_number}, table ${roll.table_number}, turn ${roll.turn_number}, roll ${roll.roll_number}: ${roll.dice.join(" · ")}`;
        return item;
    });

    if (append) content.append(...rows);
    else content.replaceChildren(...rows);
    const more = document.getElementById("history-more");
    more.hidden = !result.pagination.has_next;
}

async function openHistory(tournamentId, tournamentName) {
    historyTournamentId = tournamentId;
    historyPage = 1;
    document.getElementById("history-title").textContent = `${tournamentName}\u00a0— roll\u00a0history`;
    await loadHistory();
    modal.showModal();
}

document.getElementById("comparison-form").addEventListener("submit", submitComparison);
document.getElementById("history-close").addEventListener("click", () => modal.close());

modal.addEventListener("click", (event) => {
    if (event.target === modal) modal.close();
});

document.getElementById("history-more").addEventListener("click", async () => {
    historyPage += 1;
    await loadHistory(true);
});
