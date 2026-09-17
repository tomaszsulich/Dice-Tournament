(() => {
  "use strict";

  const form = document.getElementById("set-password-form");
  const error = document.getElementById("form-error");
  const success = document.getElementById("form-success");
  const params = new URLSearchParams(window.location.search);

  const resetCredentials = {
    uid: params.get("uid"),
    token: params.get("token"),
  };

  if (window.location.search) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  if (!resetCredentials.uid || !resetCredentials.token) {
    error.textContent = "This password reset link is incomplete or no longer available.";
    error.hidden = false;
    form.querySelector("button[type='submit']").disabled = true;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    success.hidden = true;

    const data = new FormData(form);
    const newPassword = String(data.get("new_password") || "");
    const repeatPassword = String(data.get("repeat_password") || "");

    if (newPassword !== repeatPassword) {
      error.textContent = "The passwords do not match.";
      error.hidden = false;
      return;
    }

    const button = form.querySelector("button[type='submit']");
    button.disabled = true;

    try {
      const response = await window.DiceAuth.request(
        "/api/auth/users/reset-password-confirm/",
        {
          method: "POST",
          body: JSON.stringify({
            uid: resetCredentials.uid,
            token: resetCredentials.token,
            new_password: newPassword,
          }),
        },
      );

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(window.DiceAuth.messageFrom(payload, "The reset link is invalid or has expired."));
      }

      resetCredentials.uid = null;
      resetCredentials.token = null;
      form.reset();

      success.textContent = "Your password has been changed. You can sign in now.";
      success.hidden = false;

      button.disabled = true;
    } catch (requestError) {
      error.textContent = requestError.message;

      error.hidden = false;
      button.disabled = false;
    }
  });
})();
