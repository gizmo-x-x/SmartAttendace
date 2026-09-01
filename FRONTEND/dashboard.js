const AUTH_TOKEN_D = localStorage.getItem("snapattend_token");
const API_D = "https://smartattendace.onrender.com";
let userPlan = "basic";

async function apiGet(path) {
  const response = await fetch(API_D + path, { headers: { Authorization: `Bearer ${AUTH_TOKEN_D}` } });
  return { ok: response.ok, data: await response.json().catch(() => ({})) };
}

async function loadDashboard() {
  const { ok, data } = await apiGet("/me");
  if (!ok) { window.location.href = "auth.html"; return; }

  userPlan = data.plan;
  localStorage.setItem("snapattend_plan", userPlan);
  document.getElementById("loggedInAs").textContent = `Logged in as: ${data.username}`;
  document.getElementById("planBanner").textContent =
    userPlan === "premium" ? "SnapAttend Premium — your study companion" : "SnapAttend Basic";

  document.getElementById("upgradeBanner").hidden = userPlan === "premium";
  document.getElementById("courseOutlineLock").hidden = userPlan === "premium";
  document.getElementById("studyAssistantLock").hidden = userPlan === "premium";
  document.getElementById("studyProgressSection").hidden = userPlan !== "premium";

  loadAttendanceByCourse();
  loadRecentHistory();
  loadNotificationSettings();
  if (userPlan === "premium") loadStudyProgress();
}

async function loadAttendanceByCourse() {
  const list = document.getElementById("attendanceByCourseList");
  const { ok, data } = await apiGet("/attendance-by-course");
  if (!ok || !data.courses || data.courses.length === 0) {
    list.textContent = "No confirmed attendance yet.";
    return;
  }
  list.innerHTML = data.courses.map(c => `<p><strong>${c.course_name}</strong> — Attendance: ${c.percentage}%</p>`).join("");
}

async function loadRecentHistory() {
  const list = document.getElementById("recentHistoryList");
  const { ok, data } = await apiGet("/attendance-history");
  if (!ok || !data.sessions || data.sessions.length === 0) {
    list.textContent = "No attendance confirmed yet.";
    return;
  }
  const recent = data.sessions.slice(0, 5);
  list.innerHTML = recent.map(s =>
    `<p>${s.course_name} — ${new Date(s.confirmed_at).toLocaleString()} — ${s.student_count} student(s)</p>`
  ).join("");
}

async function loadStudyProgress() {
  const list = document.getElementById("studyProgressList");
  const { ok, data } = await apiGet("/study-progress");
  if (!ok || !data.progress || data.progress.length === 0) {
    list.textContent = "No courses yet. Add one in Course Outlines.";
    return;
  }
  list.innerHTML = data.progress.map(p =>
    `<p><strong>${p.course_code || ""} ${p.course_name}</strong> — ${p.completed_topics || 0} / ${p.total_topics || 0} topics completed</p>`
  ).join("");
}

async function loadNotificationSettings() {
  const { ok, data } = await apiGet("/notification-settings");
  if (!ok) return;
  document.getElementById("attendanceEmailToggle").checked = data.attendance_confirmed_emails;
  document.getElementById("studyReminderToggle").checked = data.study_reminder_emails;
}

document.getElementById("saveNotifBtn").addEventListener("click", async function () {
  await fetch(API_D + "/notification-settings", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${AUTH_TOKEN_D}` },
    body: JSON.stringify({
      attendance_confirmed_emails: document.getElementById("attendanceEmailToggle").checked,
      study_reminder_emails: document.getElementById("studyReminderToggle").checked,
    }),
  });
  document.getElementById("notifMessage").textContent = "Saved.";
});

function goToPremiumFeature(url) {
  if (userPlan === "premium") {
    window.location.href = url;
  } else {
    window.location.href = `upgrade.html?feature=${encodeURIComponent(url)}`;
  }
}

document.getElementById("courseOutlineBtn").addEventListener("click", () => goToPremiumFeature("courses.html"));
document.getElementById("studyAssistantBtn").addEventListener("click", () => goToPremiumFeature("study.html"));

document.getElementById("upgradeBtn").addEventListener("click", async function () {
  if (!confirm("This is a placeholder for future payment integration. Upgrade to Premium now for free (testing)?")) return;
  const response = await fetch(API_D + "/upgrade", { method: "POST", headers: { Authorization: `Bearer ${AUTH_TOKEN_D}` } });
  if (response.ok) { alert("Upgraded!"); loadDashboard(); }
});

document.addEventListener("DOMContentLoaded", loadDashboard);

async function loadSubscriptionStatus() {
  const { data } = { data: (await apiGet("/me")).data };
  const statusText = document.getElementById("subStatusText");
  if (data.plan === "premium" && data.trial_end && new Date(data.trial_end) > new Date()) {
    statusText.textContent = `Free trial active until ${new Date(data.trial_end).toLocaleDateString()}.`;
  } else if (data.subscription_status === "active" && data.subscription_end) {
    statusText.textContent = `Premium active until ${new Date(data.subscription_end).toLocaleDateString()}.`;
  } else {
    statusText.textContent = "You're on Basic. Subscribe to unlock Premium.";
  }
}

document.getElementById("subscribeBtn").addEventListener("click", async function () {
  const response = await fetch(API_D + "/subscribe/initialize", {
    method: "POST",
    headers: { Authorization: `Bearer ${AUTH_TOKEN_D}` },
  });
  const result = await response.json();
  if (response.ok) {
    localStorage.setItem("snapattend_pending_ref", result.reference);
    window.open(result.authorization_url, "_blank");
    alert("Complete the bank transfer in the new tab, then come back and click 'Check Payment Status'.");
  } else {
    alert(result.error || "Could not start payment.");
  }
});

loadSubscriptionStatus();
document.getElementById("checkPaymentBtn").addEventListener("click", async function () {
  const ref = localStorage.getItem("snapattend_pending_ref");
  if (!ref) return alert("No pending payment found. Click 'Pay via Bank Transfer' first.");
  const response = await fetch(`${API_D}/subscribe/verify/${ref}`, {
    headers: { Authorization: `Bearer ${AUTH_TOKEN_D}` },
  });
  const result = await response.json();
  alert(result.message || result.error);
  if (response.ok) { localStorage.removeItem("snapattend_pending_ref"); loadDashboard(); }
});