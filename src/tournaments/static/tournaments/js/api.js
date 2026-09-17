let refreshPromise = null;

function csrfToken() {
    return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1] ?? "";
}

async function refreshAccess() {
    if (!refreshPromise) {
        refreshPromise = fetch("/api/auth/jwt/refresh/", {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken() },
        }).finally(() => {
            refreshPromise = null;
        });
    }

    return refreshPromise;
}

export async function apiRequest(url, options = {}, retry = true) {
    const response = await fetch(url, {
        credentials: "same-origin",
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" }: {}),
            ...(options.method && options.method !== "GET"
                ? { "X-CSRFToken": csrfToken() }
                : {}),
            ...(options.headers ?? {}),
        }
    });

    if (response.status === 401 && retry) {
        const refreshed = await refreshAccess();

        if (refreshed.ok) {
            return apiRequest(url, options, false);
        }

        throw new Error("RELOGIN_REQUIRED");
    }

    return response;
}
