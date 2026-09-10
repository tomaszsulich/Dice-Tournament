(() => {
  "use strict";

  const summary = document.getElementById("profile-summary");
  const details = document.getElementById("profile-details");
  const createLink = document.getElementById("create-profile-link");
  const editLink = document.getElementById("edit-profile-link");
  const error = document.getElementById("form-error");
  const logoutButton = document.getElementById("logout-button");

  async function loadProfile() {
    const response = await DiceAuth.request("/api/profile/");

    if (response.status === 401) {
      DiceAuth.redirectToLogin();
      return;
    }

    if (response.status === 404) {
      summary.textContent = "No player\u00a0profile yet. Create one when you want to play.";
      createLink.hidden = false;
      return;
    }

    if (!response.ok) {
      error.textContent = "Profile could not be loaded. Try\u00a0again.";
      error.hidden = false;
      return;
    }

    const profile = await response.json();

    summary.textContent = "Player\u00a0profile ready.";
    document.getElementById("profile-display-name").textContent = profile.display_name;
    document.getElementById("profile-nickname").textContent = profile.nickname || "—";
    details.hidden = false;
    editLink.hidden = false;
  }

  logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    const ok = await DiceAuth.logout();

    if (ok) {
      window.location.assign("/login/");
      return;
    }

    error.textContent = "Sign out failed. Try\u00a0again.";
    error.hidden = false;
    logoutButton.disabled = false;
  });

  loadProfile();
})();
