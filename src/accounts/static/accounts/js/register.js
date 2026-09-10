(() => {
  "use strict";
  const form = document.querySelector("#register-form");
  const choice = document.querySelector("#create-profile");
  const profileFields = document.querySelector("#profile-fields");
  const error = document.querySelector("#form-error");

  function syncProfileFields() {
    profileFields.hidden = !choice.checked;
    form.elements.display_name.required = choice.checked;
  }

  choice.addEventListener("change", syncProfileFields);
  syncProfileFields();

  form.addEventListener("submit", async event => {
    event.preventDefault();
    error.hidden = true;

    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    const data = new FormData(form);

    try {
      const registration = await DiceAuth.request("/api/auth/users/", {
        method: "POST",
        body: JSON.stringify({username: data.get("username"), email: data.get("email"), password: data.get("password")}),
      });

      const registrationPayload = await registration.json().catch(() => ({}));
      if (!registration.ok) throw new Error(DiceAuth.messageFrom(registrationPayload, "Account creation failed. Check the form and try again."));

      const login = await DiceAuth.request("/api/auth/jwt/create/", {
        method: "POST",
        body: JSON.stringify({username: data.get("username"), password: data.get("password")}),
      });

      const loginPayload = await login.json().catch(() => ({}));
      if (!login.ok) throw new Error("Your account was created, but automatic sign-in failed. Please sign in.");

      if (choice.checked) {
        const profile = await DiceAuth.request("/api/profile/", {
          method: "POST",
          body: JSON.stringify({display_name: data.get("display_name"), nickname: data.get("nickname") || ""}),
        });

        const profilePayload = await profile.json().catch(() => ({}));
        if (!profile.ok) throw new Error(DiceAuth.messageFrom(profilePayload, "Your account was created, but the player profile could not be created."));
      }

      window.location.assign(DiceAuth.safeNext() || "/profile/");
    } catch (exc) {
      error.textContent = exc.message;

      error.hidden = false;
      button.disabled = false;
    }
  });
})();
