(() => {
  "use strict";

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  async function request(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) {
      const token = csrfToken();
      if (token) headers.set("X-CSRFToken", token);
    }
    return fetch(url, {...options, headers, credentials: "same-origin"});
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

  window.DiceAuth = {request, messageFrom, safeNext, redirectToLogin, logout};
})();
