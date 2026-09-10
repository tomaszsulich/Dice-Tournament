(() => {
  "use strict";

  const form = document.getElementById("profile-edit-form");
  const error = document.getElementById("form-error");
  const button = form.querySelector("button[type='submit']");
  let original = null;

  async function loadProfile() {
    const response = await DiceAuth.request("/api/profile/");

    if (response.status === 401) {
      DiceAuth.redirectToLogin();
      return;
    }

    if (response.status === 404) {
      window.location.replace("/profile/setup/");
      return;
    }

    if (!response.ok) {
      error.textContent = "Profile could not be loaded. Try again.";
      error.hidden = false;
      button.disabled = true;
      return;
    }

    const profile = await response.json();

    original = {
      display_name: profile.display_name,
      nickname: profile.nickname || "",
    };

    form.elements.display_name.value = original.display_name;
    form.elements.nickname.value = original.nickname;
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    error.hidden = true;

    const next = {
      display_name: form.elements.display_name.value.trim(),
      nickname: form.elements.nickname.value.trim(),
    };

    if (original && next.display_name === original.display_name && next.nickname === original.nickname) {
      error.textContent = "Change at least one profile field before saving.";
      error.hidden = false;
      return;
    }

    button.disabled = true;

    const response = await DiceAuth.request("/api/profile/", {
      method: "PATCH",
      body: JSON.stringify(next),
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {

      if (payload.code === "PLAYER_PROFILE_UNCHANGED") {
        error.textContent = "Change at least one profile field before saving.";
      } else if (response.status === 400) {
        error.textContent = "Check the profile fields and try again.";
      } else {
        error.textContent = "Profile could not be updated. Try again.";
      }

      error.hidden = false;
      button.disabled = false;
      return;
    }

    window.location.assign("/profile/?updated=1");
  });

  loadProfile();
})();
