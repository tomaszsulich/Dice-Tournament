import { apiRequest } from "./api.js";

const BACKOFF_MS = [1000, 2000, 4000, 8000];
const DISCONNECTED_AFTER_MS = 30000;

function websocketUrl(gameId) {
    const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${scheme}//${window.location.host}/ws/tables/${gameId}/`;
}

function safeTargetUrl(targetUrl) {
    const url = new URL(targetUrl, window.location.origin);

    if (url.origin !== window.location.origin) {
        throw new Error("INVALID_ASSIGNMENT_URL");
    }

    return url.pathname + url.search + url.hash;
}

export function startRealtime({
    gameId,
    getStateVersion,
    applySnapshot,
    setConnectionState,
    setConnectionError,
}) {
    let socket = null;
    let retryTimer = null;
    let disconnectedTimer = null;
    let reconnectAttempt = 0;
    let stopped = false;
    let syncPromise = null;

    function clearRetryTimer() {
        if (retryTimer !== null) {
            window.clearTimeout(retryTimer);
            retryTimer = null;
        }
    }

    function clearDisconnectedTimer() {
        if (disconnectedTimer !== null) {
            window.clearTimeout(disconnectedTimer);
            disconnectedTimer = null;
        }
    }

    function beginDisconnectedTimer() {
        if (disconnectedTimer !== null) return;

        disconnectedTimer = window.setTimeout(() => {
            setConnectionState("disconnected");
        }, DISCONNECTED_AFTER_MS);
    }

    async function confirmAssignment(data) {
        if (
            data?.code !== "TABLE_ASSIGNMENT_CHANGED" ||
            !Number.isInteger(data.table_id) ||
            typeof data.target_url !== "string"
        ) {
            throw new Error("INVALID_ASSIGNMENT");
        }

        const response = await apiRequest(`/api/games/${data.table_id}/state/`);

        if (!response.ok) {
            throw new Error("ASSIGNMENT_SNAPSHOT_FAILED");
        }

        const targetSnapshot = await response.json();

        if (targetSnapshot.game_id !== data.table_id) {
            throw new Error("ASSIGNMENT_SNAPSHOT_MISMATCH");
        }

        window.location.assign(safeTargetUrl(data.target_url));
    }

    async function fetchAuthoritativeSnapshot() {
        const response = await apiRequest(`/api/games/${gameId}/state/`);

        if (response.status === 409) {
            await confirmAssignment(await response.json());
            return null;
        }

        if (!response.ok) {
            throw new Error(response.status === 403 ? "PARTICIPATION_UNAVAILABLE" : "SNAPSHOT_FAILED");
        }

        const next = await response.json();
        applySnapshot(next);
        return next;
    }

    function syncSnapshot() {
        if (!syncPromise) {
            syncPromise = fetchAuthoritativeSnapshot().finally(() => {
                syncPromise = null;
            });
        }

        return syncPromise;
    }

    async function handleMessage(event) {
        let message;

        try {
            message = JSON.parse(event.data);
        } catch {
            return;
        }

        if (message.type === "table_assignment_changed") {
            await confirmAssignment({
                code: "TABLE_ASSIGNMENT_CHANGED",
                table_id: message.table_id,
                target_url: message.target_url,
            });
            return;
        }

        if (message.type !== "table_changed" || message.table_id !== gameId) return;

        if (!Number.isInteger(message.state_version)) return;
        if (message.state_version <= getStateVersion()) return;

        await syncSnapshot();
    }

    function scheduleReconnect() {
        if (stopped || retryTimer !== null) return;

        setConnectionState("reconnecting");
        beginDisconnectedTimer();

        const delay = BACKOFF_MS[Math.min(reconnectAttempt, BACKOFF_MS.length - 1)];
        reconnectAttempt += 1;

        retryTimer = window.setTimeout(() => {
            retryTimer = null;
            connect();
        }, delay);
    }

    async function handleRejectedConnection(closeCode) {
        try {
            const response = await apiRequest(`/api/games/${gameId}/state/`);

            if (response.status === 409) {
                await confirmAssignment(await response.json());
                return;
            }

            if (response.ok && closeCode === 4401) {
                scheduleReconnect();
                return;
            }

            if (response.status === 403 || closeCode === 4403) {
                stopped = true;
                clearRetryTimer();
                setConnectionState("terminal");
                setConnectionError("Your tournament participation is no longer active.");
                return;
            }

            scheduleReconnect();
        } catch (error) {
            if (error.message === "RELOGIN_REQUIRED") {
                stopped = true;
                clearRetryTimer();
                clearDisconnectedTimer();
                setConnectionState("terminal");
                setConnectionError("Session expired. Sign in again.");
                return;
            }

            scheduleReconnect();
        }
    }

    function connect() {
        if (stopped) return;

        clearRetryTimer();
        setConnectionState("reconnecting");
        const connection = new WebSocket(websocketUrl(gameId));
        socket = connection;

        connection.addEventListener("open", async () => {
            try {
                await syncSnapshot();
                reconnectAttempt = 0;
                clearDisconnectedTimer();
                setConnectionError("");
                setConnectionState("connected");
            } catch (error) {
                if (error.message === "RELOGIN_REQUIRED") {
                    stopped = true;
                    clearRetryTimer();
                    clearDisconnectedTimer();
                    if (connection.readyState === WebSocket.OPEN) {
                        connection.close();
                    }
                    setConnectionState("terminal");
                    setConnectionError("Session expired. Sign in again.");
                    return;
                }

                if (connection.readyState === WebSocket.OPEN) {
                    connection.close();
                }
            }
        });

        connection.addEventListener("message", (event) => {
            handleMessage(event).catch(() => {
                setConnectionError("Could not restore the latest table state.");
            });
        });

        connection.addEventListener("close", (event) => {
            if (socket === connection) {
                socket = null;
            }

            if (stopped) return;

            if (event.code === 4401 || event.code === 4403) {
                handleRejectedConnection(event.code);
                return;
            }

            scheduleReconnect();
        });
    }

    function stop() {
        stopped = true;
        clearRetryTimer();
        clearDisconnectedTimer();

        if (socket !== null) {
            socket.close(1000);
            socket = null;
        }
    }

    connect();

    return {
        reloadSnapshot: syncSnapshot,
        stop,
    };
}
