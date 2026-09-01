const TOKEN_S = localStorage.getItem("snapattend_token");
const API_S = "http://127.0.0.1:5000";

let lastExplanation = "";

document.getElementById("analyzeBtn").addEventListener("click", async function () {
  const courseName = document.getElementById("courseNameField").value.trim();
  const topicTitle = document.getElementById("topicTitleField").value.trim();
  const topicDesc = document.getElementById("topicDescField").value.trim();
  const resultBox = document.getElementById("analysisResult");

  if (!courseName || !topicTitle) {
    alert("Please enter a course name and topic.");
    return;
  }

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
      lastExplanation = result.text;
      document.getElementById("followupSection").hidden = false;
    } else {
      resultBox.textContent = "Error: " + (result.error || "Could not analyze topic.");
    }
  } catch (err) {
    resultBox.textContent = "Could not reach the server.";
  }
});

document.getElementById("followupBtn").addEventListener("click", async function () {
  const question = document.getElementById("followupInput").value.trim();
  const courseName = document.getElementById("courseNameField").value.trim();
  const topicTitle = document.getElementById("topicTitleField").value.trim();
  const resultBox = document.getElementById("followupResult");

  if (!question) return alert("Please type a question.");

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
    resultBox.textContent = response.ok ? result.text : "Error: " + (result.error || "Could not get an answer.");
  } catch (err) {
    resultBox.textContent = "Could not reach the server.";
  }
});