(() => {
  "use strict";

  const ASSIGNMENT_BACKOFF_MS = [1000, 2000, 4000, 8000];
  const ASSIGNMENT_REDIRECT_EXEMPT_PATHS = new Set([
    "/login/",
    "/register/",
    "/forgot-password/",
    "/set-password/",
  ]);
  let refreshPromise = null;

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  async function refreshAccess() {
    if (!refreshPromise) {
      refreshPromise = fetch("/api/auth/jwt/refresh/", {
        method: "POST",
        credentials: "same-origin",
        headers: {"X-CSRFToken": csrfToken()},
      }).finally(() => {
        refreshPromise = null;
      });
    }

    return refreshPromise;
  }

  async function request(url, options = {}, retry = true) {
    const headers = new Headers(options.headers || {});
    if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) {
      const token = csrfToken();
      if (token) headers.set("X-CSRFToken", token);
    }

    const response = await fetch(url, {...options, headers, credentials: "same-origin"});

    if (response.status === 401 && retry) {
      const refreshed = await refreshAccess();

      if (refreshed.ok) return request(url, options, false);
    }

    return response;
  }

  function messageFrom(data, fallback) {
    if (!data || typeof data !== "object") return fallback;
    if (typeof data.message === "string") return data.message;
    if (typeof data.detail === "string") return data.detail;
    const first = Object.values(data).find(value => Array.isArray(value) && value.length);
    return first ? String(first[0]) : fallback;
  }

  function safeNext() {
    const value = new URLSearchParams(window.location.search).get("next");
    if (!value) return null;
    try {
      const target = new URL(value, window.location.origin);
      return target.origin === window.location.origin ? `${target.pathname}${target.search}${target.hash}` : null;
    } catch { return null; }
  }

  function redirectToLogin() {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    window.location.replace(`/login/?next=${next}`);
  }

  async function logout() {
    const response = await request("/api/auth/logout/", {method: "POST"});
    return response.ok;
  }

  function safeAssignmentTarget(targetUrl) {
    const target = new URL(targetUrl, window.location.origin);
    if (target.origin !== window.location.origin) throw new Error("INVALID_ASSIGNMENT_URL");
    return `${target.pathname}${target.search}${target.hash}`;
  }

  function redirectToActiveGame(payload) {
    if (
      payload?.code !== "ACTIVE_GAME_IN_PROGRESS" ||
      typeof payload?.details?.target_url !== "string"
    ) {
      return false;
    }

    window.location.assign(safeAssignmentTarget(payload.details.target_url));
    return true;
  }

  function startAssignmentRedirects() {
    const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socketUrl = `${scheme}//${window.location.host}/ws/participant/assignments/`;
    let attempt = 0;
    let stopped = false;
    let retryTimer = null;

    function scheduleReconnect() {
      if (stopped || retryTimer !== null) return;

      const delay = ASSIGNMENT_BACKOFF_MS[Math.min(attempt, ASSIGNMENT_BACKOFF_MS.length - 1)];
      attempt += 1;
      retryTimer = window.setTimeout(() => {
        retryTimer = null;
        connect();
      }, delay);
    }

    async function handleRejectedConnection(closeCode) {
      if (closeCode === 4403) {
        stopped = true;
        return;
      }

      if (closeCode !== 4401) {
        scheduleReconnect();
        return;
      }

      const response = await request("/api/profile/");

      if (response.status === 401) {
        stopped = true;
        redirectToLogin();
        return;
      }

      attempt = 0;
      scheduleReconnect();
    }

    function connect() {
      if (stopped) return;

      const socket = new WebSocket(socketUrl);

      socket.addEventListener("open", () => {
        attempt = 0;
      });

      socket.addEventListener("message", event => {
        let message;
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }

        if (message.type !== "table_assignment_changed") return;

        try {
          window.location.assign(safeAssignmentTarget(message.target_url));
        } catch {
          socket.close();
        }
      });

      socket.addEventListener("close", event => {
        handleRejectedConnection(event.code).catch(scheduleReconnect);
      });
    }

    connect();
  }

  window.DiceAuth = {
    request,
    messageFrom,
    safeNext,
    redirectToLogin,
    redirectToActiveGame,
    logout,
  };

  if (!ASSIGNMENT_REDIRECT_EXEMPT_PATHS.has(window.location.pathname)) {
    startAssignmentRedirects();
  }
})();
