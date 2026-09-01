const TOKEN_U = localStorage.getItem("snapattend_token");

document.getElementById("upgradeNowBtn").addEventListener("click", async function () {
  const confirmed = confirm("This is a placeholder for future payment integration. Upgrade to Premium now for free (testing)?");
  if (!confirmed) return;

  try {
    const response = await fetch("https://smartattendace.onrender.com/upgrade", {
      method: "POST",
      headers: { Authorization: `Bearer ${TOKEN_U}` },
    });
    if (response.ok) {
      localStorage.setItem("snapattend_plan", "premium");
      const params = new URLSearchParams(window.location.search);
      const feature = params.get("feature");
      window.location.href = feature || "dashboard.html";
    } else {
      document.getElementById("upgradeMessage").textContent = "Could not upgrade. Try again.";
    }
  } catch (err) {
    document.getElementById("upgradeMessage").textContent = "Could not reach the server.";
  }
});