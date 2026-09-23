const TOKEN_S = localStorage.getItem("snapattend_token");
const API_S = "https://smartattendace.onrender.com";

function renderMath(el) {
  if (window.renderMathInElement) {
    renderMathInElement(el, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false }
      ]
    });
  }
}

let bannerTimeout = null;

function showBanner(message, type) {
  const banner = document.getElementById("floatingBanner");
  clearTimeout(bannerTimeout);
  banner.textContent = message;
  banner.className = type === "success" ? "success show" : "show";
  bannerTimeout = setTimeout(() => {
    banner.classList.remove("show");
  }, 5000);
}

let lastExplanation = "";

document.getElementById("analyzeBtn").addEventListener("click", async function () {
  const courseName = document.getElementById("courseNameField").value.trim();
  const topicTitle = document.getElementById("topicTitleField").value.trim();
  const topicDesc = document.getElementById("topicDescField").value.trim();
  const resultBox = document.getElementById("analysisResult");
  const analyzeBtn = document.getElementById("analyzeBtn");

  if (!courseName || !topicTitle) {
    showBanner("Please enter a course name and topic.", "error");
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";
  resultBox.textContent = "Analyzing...";

  try {
    const response = await fetch(`${API_S}/study-assistant/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN_S}` },
      body: JSON.stringify({ course_name: courseName, topic_title: topicTitle, topic_description: topicDesc }),
    });
    const result = await response.json();
    if (response.ok) {
      resultBox.textContent = result.text;
      renderMath(resultBox);
      lastExplanation = result.text;
      document.getElementById("followupSection").hidden = false;
    } else {
      resultBox.textContent = "";
      showBanner(result.error || "Could not analyze topic. Please try again.", "error");
    }
  } catch (err) {
    resultBox.textContent = "";
    showBanner("Could not reach the server. Please try again.", "error");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Topic";
  }
});

document.getElementById("followupBtn").addEventListener("click", async function () {
  const question = document.getElementById("followupInput").value.trim();
  const courseName = document.getElementById("courseNameField").value.trim();
  const topicTitle = document.getElementById("topicTitleField").value.trim();
  const resultBox = document.getElementById("followupResult");
  const followupBtn = document.getElementById("followupBtn");

  if (!question) {
    showBanner("Please type a question.", "error");
    return;
  }

  followupBtn.disabled = true;
  followupBtn.textContent = "Thinking...";
  resultBox.textContent = "Thinking...";

  try {
    const response = await fetch(`${API_S}/study-assistant/followup`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN_S}` },
      body: JSON.stringify({
        course_name: courseName,
        topic_title: topicTitle,
        previous_explanation: lastExplanation,
        question: question,
      }),
    });
    const result = await response.json();
    if (response.ok) {
      resultBox.textContent = result.text;
      renderMath(resultBox);
    } else {
      resultBox.textContent = "";
      showBanner(result.error || "Could not get an answer. Please try again.", "error");
    }
  } catch (err) {
    resultBox.textContent = "";
    showBanner("Could not reach the server. Please try again.", "error");
  } finally {
    followupBtn.disabled = false;
    followupBtn.textContent = "Ask";
  }
});