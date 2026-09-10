(() => {
  "use strict";
  const form = document.querySelector("#profile-form");
  const error = document.querySelector("#form-error");
  const success = document.querySelector("#form-success");
  const button = form.querySelector("button[type='submit']");

  async function load() {
    const response = await DiceAuth.request("/api/profile/");

    if (response.status === 401) {
      DiceAuth.redirectToLogin();
      return;
    }

    if (response.ok) {
      const profile = await response.json();
      form.elements.display_name.value = profile.display_name;
      form.elements.nickname.value = profile.nickname || "";
      for (const element of form.elements) element.disabled = true;
      success.textContent = new URLSearchParams(location.search).has("created") ? "Player profile created." : "Player profile ready.";
      success.hidden = false;
    }
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    error.hidden = true;
    button.disabled = true;
    const data = new FormData(form);

    const response = await DiceAuth.request("/api/profile/", {
      method: "POST",
      body: JSON.stringify({display_name: data.get("display_name"), nickname: data.get("nickname") || ""}),
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      error.textContent = DiceAuth.messageFrom(payload, "Player profile could not be created. Try again.");
      error.hidden = false;
      button.disabled = false;
      return;
    }

    window.location.assign(DiceAuth.safeNext() || "/profile/?created=1");
  });

  load();
})();
