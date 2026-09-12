import { apiRequest } from "./api.js";

const root = document.querySelector(".dashboard");
const tournamentId = root.dataset.tournamentId;

let snapshot = JSON.parse(document.getElementById("initial-organizer-dashboard").textContent);
let selectedTableId = null;
let reconnectAttempt = 0;
let reconnectTimer = null;
let refreshPromise = null;
let stopped = false;

const reconnectDelays = [1000, 2000, 4000, 8000];

function websocketUrl() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws/tournaments/${tournamentId}/organizers/`;
}

function tableCard(table) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "table-card";

    button.dataset.tableId = table.id;
    button.dataset.state = table.state;
    button.dataset.attention = String(table.requires_attention);
    button.dataset.participantIds = table.participant_ids.join(" ");

    button.innerHTML = `
        <span class="table-card__top"><h3></h3><span class="state"></span></span>
        <dl>
            <dt>Participant</dt><dd class="participant"></dd>
            <dt>Turn&nbsp;/&nbsp;roll</dt><dd class="turn"></dd>
            <dt>Last&nbsp;action</dt><dd class="action"></dd>
            <dt>Round</dt><dd class="round"></dd>
        </dl>`;

    button.querySelector("h3").textContent = table.label;
    button.querySelector(".state").textContent = table.state;
    button.querySelector(".participant").textContent = table.current_participant?.name ?? "—";

    button.querySelector(".turn").textContent = table.turn_number
        ? `${table.turn_number}\u00a0/\u00a0${table.roll_number}`
        : "—";

    button.querySelector(".action").textContent = table.last_action;
    button.querySelector(".round").textContent = table.round.name || `Round ${table.round.number}`;
    button.addEventListener("click", () => showDetail(table.id));
    return button;
}

function renderSummary() {
    Object.entries(snapshot.summary).forEach(([key, value]) => {
        const counter = document.getElementById(`summary-${key}`);
        if (counter) counter.textContent = value;
    });
}

function renderCards(onlyTableId = null) {
    const grid = document.getElementById("table-grid");
    const filter = document.getElementById("table-filter").value;

    const visible = snapshot.tables.filter((table) => (
        filter === "all"
        || table.state === filter
        || (filter === "attention" && table.requires_attention)
    ));

    if (onlyTableId !== null) {
        const table = visible.find((item) => item.id === onlyTableId);
        const existing = grid.querySelector(`[data-table-id="${onlyTableId}"]`);
        if (table && existing) existing.replaceWith(tableCard(table));
        else renderCards();
        return;
    }

    grid.replaceChildren(...visible.map(tableCard));
}

function renderAttention() {
    const list = document.getElementById("attention-list");
    document.getElementById("attention-count").textContent = snapshot.attention.length;

    if (!snapshot.attention.length) {
        const empty = document.createElement("p");
        empty.className = "empty";
        empty.textContent = "No\u00a0tables require attention.";
        list.replaceChildren(empty);
        return;
    }

    list.replaceChildren(...snapshot.attention.map((item) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "attention-item";

        const label = document.createElement("strong");
        const reason = document.createElement("span");
        label.textContent = item.label;

        reason.textContent = item.reasons.join(" · ");
        button.append(label, reason);
        button.addEventListener("click", () => showDetail(item.table_id));
        return button;
    }));
}

function showDetail(tableId) {
    const table = snapshot.tables.find((item) => item.id === tableId);
    if (!table) return;
    selectedTableId = tableId;
    document.getElementById("detail-title").textContent = table.label;
    const content = document.getElementById("detail-content");

    const rows = [
        ["State", table.state],
        ["Current\u00a0participant", table.current_participant?.name ?? "—"],
        ["Turn\u00a0/\u00a0roll", table.turn_number ? `${table.turn_number}\u00a0/\u00a0${table.roll_number}` : "—"],
        ["Last\u00a0action", table.last_action],
        ["Attention", table.attention_reasons.join(" · ") || "No"],
    ];

    content.replaceChildren(...rows.flatMap(([term, value]) => {
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = term;
        dd.textContent = value;
        return [dt, dd];
    }));

    document.getElementById("table-detail").hidden = false;
}

async function refresh(targetTableId = null) {
    if (!refreshPromise) {
        refreshPromise = apiRequest(`/api/tournaments/${tournamentId}/organizer-dashboard/`)
            .then(async (response) => {
                if (!response.ok) throw new Error(`DASHBOARD_${response.status}`);
                return response.json();
            })
            .finally(() => { refreshPromise = null; });
    }

    snapshot = await refreshPromise;
    renderSummary();
    renderAttention();
    renderCards(targetTableId);

    if (selectedTableId !== null && (targetTableId === null || selectedTableId === targetTableId)) {
        showDetail(selectedTableId);
    }
}

function stopWith(message, offerSignIn = false) {
    stopped = true;
    window.clearTimeout(reconnectTimer);
    const status = document.getElementById("connection-state");
    status.replaceChildren(document.createTextNode(message));

    if (offerSignIn) {
        const link = document.createElement("a");
        const returnTo = `${window.location.pathname}${window.location.search}`;
        link.href = `/login/?next=${encodeURIComponent(returnTo)}`;
        link.textContent = "Sign\u00a0in again";
        status.append(" ", link);
    }
}

async function verifyAccess() {
    try {
        await refresh();
        return true;

    } catch (error) {
        if (error.message === "DASHBOARD_403" || error.message === "DASHBOARD_404") {
            stopWith("Organizer access is no longer available.");
            return false;
        }

        if (error.message === "RELOGIN_REQUIRED") {
            stopWith("Session expired.", true);
            return false;
        }

        return true;
    }
}

function scheduleReconnect() {
    if (stopped) return;
    const delay = reconnectDelays[Math.min(reconnectAttempt, reconnectDelays.length - 1)];
    reconnectAttempt += 1;
    reconnectTimer = window.setTimeout(connect, delay);
}

function connect() {
    if (stopped) return;
    const status = document.getElementById("connection-state");
    const socket = new WebSocket(websocketUrl());

    socket.addEventListener("open", async () => {
        try {
            await refresh();
            reconnectAttempt = 0;
            status.textContent = "Connected";
        } catch (error) {
            socket.close();
        }
    });

    socket.addEventListener("message", (event) => {
        let message;

        try {
            message = JSON.parse(event.data);
        } catch (error) {
            return;
        }

        if (message.type === "table_changed" && Number.isInteger(message.table_id)) {
            refresh(message.table_id).catch(() => socket.close());
        }

        if (message.type === "participant_connection_changed") {
            if (!Number.isInteger(message.participant_id)) return;
            const card = document.querySelector(`[data-participant-ids~="${message.participant_id}"]`);
            refresh(card ? Number(card.dataset.tableId) : null).catch(() => socket.close());
        }
    });

    socket.addEventListener("close", async (event) => {
        if (stopped) return;
        status.textContent = "Reconnecting…";
        if ((event.code === 4401 || event.code === 4403) && !(await verifyAccess())) return;
        scheduleReconnect();
    });
}

document.getElementById("table-filter").addEventListener("change", () => renderCards());

document.getElementById("detail-close").addEventListener("click", () => {
    document.getElementById("table-detail").hidden = true;
    selectedTableId = null;
});

document.addEventListener("click", (event) => {
    const detail = document.getElementById("table-detail");
    if (
        detail.hidden
        || detail.contains(event.target)
        || event.target.closest(".table-card, .attention-item")
    ) return;
    detail.hidden = true;
    selectedTableId = null;
});

document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    document.getElementById("table-detail").hidden = true;
    selectedTableId = null;
});

renderSummary();
renderCards();
renderAttention();
connect();

window.addEventListener("pagehide", () => {
    stopped = true;
    window.clearTimeout(reconnectTimer);
});
