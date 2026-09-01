const usernameInput = document.getElementById("usernameInput");
const passwordInput = document.getElementById("passwordInput");
const submitAuthBtn = document.getElementById("submitAuthBtn");
const authMessage = document.getElementById("authMessage");
const authTitle = document.getElementById("authTitle");
const switchModeText = document.getElementById("switchModeText");
const switchModeLink = document.getElementById("switchModeLink");

let mode = "login";
let pendingVerifyToken = null;

if (localStorage.getItem("snapattend_token")) {
  window.location.href = "index.html";
}

switchModeLink.addEventListener("click", function (e) {
  e.preventDefault();
  if (mode === "login") {
    mode = "register";
    authTitle.textContent = "Create an Account";
    submitAuthBtn.textContent = "Register";
    switchModeText.textContent = "Already have an account?";
    switchModeLink.textContent = "Log In";
    document.getElementById("planChoice").hidden = false;
  } else {
    mode = "login";
    authTitle.textContent = "Log In";
    submitAuthBtn.textContent = "Log In";
    switchModeText.textContent = "Don't have an account?";
    switchModeLink.textContent = "Register";
    document.getElementById("planChoice").hidden = true;
  }
  authMessage.hidden = true;
});

submitAuthBtn.addEventListener("click", async function () {
  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    showAuthMessage("Please enter a username and password.", "error");
    return;
  }

  const endpoint = mode === "login" ? "/login" : "/register";
  const originalText = submitAuthBtn.textContent;
  submitAuthBtn.disabled = true;
  submitAuthBtn.textContent = "Please wait...";

  try {
    const response = await fetch(`http://127.0.0.1:5000${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        password,
        email: document.getElementById("emailInput") ? document.getElementById("emailInput").value.trim() : "",
        plan: mode === "register" ? document.querySelector('input[name="plan"]:checked').value : undefined,
      }),
    });
    const result = await response.json();

    if (response.ok) {
      if (mode === "register") {
        pendingVerifyToken = result.token;
        document.getElementById("emailVerifyFlow").hidden = false;
        showAuthMessage("Account created! Check your email for a verification code.", "success");
      } else {
        localStorage.setItem("snapattend_token", result.token);
        localStorage.setItem("snapattend_username", result.username);
        if (result.plan) localStorage.setItem("snapattend_plan", result.plan);
        window.location.href = "dashboard.html";
      }
    } else if (result.needs_verification) {
      showAuthMessage("Please verify your email. Sending a fresh code...", "error");
      const resendResponse = await fetch("http://127.0.0.1:5000/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const resendResult = await resendResponse.json();
      if (resendResponse.ok) {
        pendingVerifyToken = resendResult.token;
        document.getElementById("emailVerifyFlow").hidden = false;
      }
    } else {
      showAuthMessage(result.error || "Something went wrong.", "error");
    }
  } catch (err) {
    showAuthMessage("Could not reach the server. Is the Flask backend running?", "error");
  } finally {
    submitAuthBtn.disabled = false;
    submitAuthBtn.textContent = originalText;
  }
});

document.getElementById("submitVerifyBtn").addEventListener("click", async function () {
  const code = document.getElementById("verifyCodeInput").value.trim();
  if (!code) return alert("Please enter the code.");

  const response = await fetch("http://127.0.0.1:5000/verify-email", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${pendingVerifyToken}` },
    body: JSON.stringify({ code }),
  });
  const result = await response.json();
  if (response.ok) {
    alert("Email verified! You can now log in.");
    window.location.reload();
  } else {
    alert(result.error || "Invalid code.");
  }
});

document.getElementById("resendCodeLink").addEventListener("click", async function (e) {
  e.preventDefault();
  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  if (!username || !password) {
    return alert("Please enter your username and password above first.");
  }
  const response = await fetch("http://127.0.0.1:5000/resend-verification", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const result = await response.json();
  if (response.ok) {
    pendingVerifyToken = result.token;
    alert("A new code has been sent.");
  } else {
    alert(result.error || "Could not resend code.");
  }
});

document.getElementById("forgotPasswordLink").addEventListener("click", function (e) {
  e.preventDefault();
  document.getElementById("forgotPasswordFlow").hidden = false;
});

document.getElementById("sendResetCodeBtn").addEventListener("click", async function () {
  const btn = this;
  const email = document.getElementById("resetEmailInput").value.trim();
  if (!email) return alert("Please enter your email.");
  btn.disabled = true;
  btn.textContent = "Sending...";
  await fetch("http://127.0.0.1:5000/request-password-reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  alert("If that email exists, a code was sent (check Flask terminal if testing locally).");
  document.getElementById("resetStep2").hidden = false;
  btn.disabled = false;
  btn.textContent = "Send Reset Code";
});

document.getElementById("submitResetBtn").addEventListener("click", async function () {
  const btn = this;
  btn.disabled = true;
  btn.textContent = "Resetting...";
  const email = document.getElementById("resetEmailInput").value.trim();
  const code = document.getElementById("resetCodeInput").value.trim();
  const new_password = document.getElementById("newPasswordInput").value;

  const response = await fetch("http://127.0.0.1:5000/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code, new_password }),
  });
  const result = await response.json();
  alert(result.message || result.error);
  if (response.ok) {
    document.getElementById("forgotPasswordFlow").hidden = true;
  }
  btn.disabled = false;
  btn.textContent = "Reset Password";
});

function showAuthMessage(text, type) {
  authMessage.textContent = text;
  authMessage.className = "message " + type;
  authMessage.hidden = false;
}

document.getElementById("toggleHelpBtn").addEventListener("click", function () {
  const content = document.getElementById("helpContent");
  content.hidden = !content.hidden;
});