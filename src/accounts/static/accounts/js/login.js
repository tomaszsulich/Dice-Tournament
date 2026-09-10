(() => {
  "use strict";
  const form = document.querySelector("#login-form");
  const error = document.querySelector("#form-error");
  let pending = false;

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (pending) return;
    pending = true;

    error.hidden = true;
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;

    try {
      const data = new FormData(form);

      const response = await DiceAuth.request("/api/auth/jwt/create/", {
        method: "POST",
        body: JSON.stringify({username: data.get("username"), password: data.get("password")}),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(DiceAuth.messageFrom(payload, "Sign-in failed. Check your details and try again."));

      window.location.assign(DiceAuth.safeNext() || "/profile/");
    } catch (exc) {
      error.textContent = exc.message;

      error.hidden = false;
      button.disabled = false;
      pending = false;
    }
  });
})();
