(() => {
  "use strict";

  const form = document.getElementById("password-reset-form");
  const error = document.getElementById("form-error");
  const success = document.getElementById("form-success");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    success.hidden = true;

    const button = form.querySelector("button[type='submit']");
    button.disabled = true;

    try {
      const data = new FormData(form);
      const response = await window.DiceAuth.request(
        "/api/auth/users/reset-password/",
        {
          method: "POST",
          body: JSON.stringify({email: data.get("email")}),
        },
      );

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(window.DiceAuth.messageFrom(payload, "The request could not be completed."));
      }

      form.reset();
      success.textContent = "If an account matches that email address, a reset link has been sent.";

      success.hidden = false;
    } catch (requestError) {
      error.textContent = requestError.message;

      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  });
})();
