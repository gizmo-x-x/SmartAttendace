const imageInput = document.getElementById("imageInput");
const uploadBtn = document.getElementById("uploadBtn");
const previewImage = document.getElementById("previewImage");
const previewPlaceholder = document.getElementById("previewPlaceholder");
const messageBox = document.getElementById("messageBox");

const aiStatusText = document.getElementById("aiStatusText");
const reviewBanner = document.getElementById("reviewBanner");
const sheetInfo = document.getElementById("sheetInfo");
const resultsTableWrapper = document.getElementById("resultsTableWrapper");
const resultsTableHead = document.getElementById("resultsTableHead");
const resultsTableBody = document.getElementById("resultsTableBody");
const reviewControls = document.getElementById("reviewControls");
const addRowBtn = document.getElementById("addRowBtn");
const downloadPdfBtn = document.getElementById("downloadPdfBtn");
const downloadExcelBtn = document.getElementById("downloadExcelBtn");
const confirmBtn = document.getElementById("confirmBtn");
const confirmMessage = document.getElementById("confirmMessage");
const rawTextDetails = document.getElementById("rawTextDetails");
const rawTextContent = document.getElementById("rawTextContent");

const pdfInput = document.getElementById("pdfInput");
const importPdfBtn = document.getElementById("importPdfBtn");

const AUTH_TOKEN = localStorage.getItem("snapattend_token");
const logoutBtn = document.getElementById("logoutBtn");
const loggedInAs = document.getElementById("loggedInAs");

const configChoiceBanner = document.getElementById("configChoiceBanner");
const configChoiceText = document.getElementById("configChoiceText");
const useLastConfigBtn = document.getElementById("useLastConfigBtn");
const startNewConfigBtn = document.getElementById("startNewConfigBtn");
const configForm = document.getElementById("configForm");
const numWeeksInput = document.getElementById("numWeeksInput");
const columnsList = document.getElementById("columnsList");
const addColumnBtn = document.getElementById("addColumnBtn");
const applyConfigBtn = document.getElementById("applyConfigBtn");
const configSummary = document.getElementById("configSummary");

const courseNameInput = document.getElementById("courseNameInput");
const loadHistoryBtn = document.getElementById("loadHistoryBtn");
const historyList = document.getElementById("historyList");
const historyDetailWrapper = document.getElementById("historyDetailWrapper");
const historyDetailTitle = document.getElementById("historyDetailTitle");
const historyDetailHead = document.getElementById("historyDetailHead");
const historyDetailBody = document.getElementById("historyDetailBody");

const ALLOWED_TYPES = ["image/jpeg", "image/png"];
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;

const VALID_FINAL_STATUSES = ["Present", "Absent", "Late", "Excused", ""];
const STATUS_OPTIONS = [
  { value: "Unclear", label: "Unclear" },
  { value: "", label: "(blank)" },
  { value: "Present", label: "Present" },
  { value: "Absent", label: "Absent" },
  { value: "Late", label: "Late" },
  { value: "Excused", label: "Excused" },
];

const DEFAULT_CONFIG = {
  numWeeks: 14,
  columns: [
    { id: "student_name", label: "Name" },
    { id: "matric_no", label: "Matric No" },
    { id: "programme", label: "Programme" },
  ],
};

let currentConfig = null;
let columnIdCounter = 1;

// ---------- TABLE CONFIGURATION ----------

function initConfig() {
  const saved = localStorage.getItem("snapattend_config");
  if (saved) {
    try {
      const parsedConfig = JSON.parse(saved);
      const labels = parsedConfig.columns.map((c) => c.label).join(", ");
      configChoiceText.textContent = `We found a saved table setup: ${parsedConfig.numWeeks} weeks, columns: ${labels}.`;
      configChoiceBanner.hidden = false;
      configForm.hidden = true;

      useLastConfigBtn.onclick = function () {
        applyConfig(parsedConfig);
        configChoiceBanner.hidden = true;
        configForm.hidden = false;
      };
      startNewConfigBtn.onclick = function () {
        configChoiceBanner.hidden = true;
        configForm.hidden = false;
        renderConfigForm(DEFAULT_CONFIG);
      };
      return;
    } catch (e) {
      // fall through to a fresh default config below
    }
  }
  renderConfigForm(DEFAULT_CONFIG);
}

function renderConfigForm(config) {
  numWeeksInput.value = config.numWeeks;
  columnsList.innerHTML = "";
  config.columns.forEach((col) => addColumnRow(col.label, col.id));
}

function addColumnRow(label, existingId) {
  const id = existingId || `field_${columnIdCounter++}`;
  const row = document.createElement("div");
  row.className = "column-row";
  row.dataset.columnId = id;

  const labelInput = document.createElement("input");
  labelInput.type = "text";
  labelInput.value = label;
  labelInput.className = "row-input column-label-input";
  row.appendChild(labelInput);

  const upBtn = document.createElement("button");
  upBtn.type = "button";
  upBtn.textContent = "Up";
  upBtn.addEventListener("click", function () {
    const prev = row.previousElementSibling;
    if (prev) columnsList.insertBefore(row, prev);
  });
  row.appendChild(upBtn);

  const downBtn = document.createElement("button");
  downBtn.type = "button";
  downBtn.textContent = "Down";
  downBtn.addEventListener("click", function () {
    const next = row.nextElementSibling;
    if (next) columnsList.insertBefore(next, row);
  });
  row.appendChild(downBtn);

  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.textContent = "Remove";
  removeBtn.addEventListener("click", function () {
    if (columnsList.children.length <= 1) {
      alert("You need at least one column.");
      return;
    }
    const confirmed = window.confirm(`Remove the "${labelInput.value || "this"}" column?`);
    if (confirmed) row.remove();
  });
  row.appendChild(removeBtn);

  columnsList.appendChild(row);
}

addColumnBtn.addEventListener("click", function () {
  addColumnRow("New Field");
});

applyConfigBtn.addEventListener("click", function () {
  const numWeeks = parseInt(numWeeksInput.value, 10);
  if (!numWeeks || numWeeks < 1 || numWeeks > 52) {
    alert("Please enter a valid number of weeks (1-52).");
    return;
  }
  const columnRows = Array.from(columnsList.children);
  if (columnRows.length === 0) {
    alert("Please add at least one column.");
    return;
  }
  const columns = [];
  for (const row of columnRows) {
    const label = row.querySelector(".column-label-input").value.trim();
    if (!label) {
      alert("Every column needs a name.");
      return;
    }
    columns.push({ id: row.dataset.columnId, label: label });
  }
  applyConfig({ numWeeks, columns });
});

function applyConfig(config) {
  currentConfig = config;
  localStorage.setItem("snapattend_config", JSON.stringify(config));
  const labels = config.columns.map((c) => c.label).join(", ");
  configSummary.textContent = `Active setup: ${config.numWeeks} weeks, columns: ${labels}`;
  renderConfigForm(config);
}

// ---------- IMAGE UPLOAD ----------

imageInput.addEventListener("change", function () {
  const file = imageInput.files[0];
  clearMessage();
  resetAiSection();
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function (event) {
    previewImage.src = event.target.result;
    previewImage.hidden = false;
    previewPlaceholder.hidden = true;
  };
  reader.readAsDataURL(file);
});

uploadBtn.addEventListener("click", async function () {
  const file = imageInput.files[0];
  clearMessage();
  resetAiSection();
  if (!file) {
    showMessage("Please select an image first.", "error");
    return;
  }
  if (!ALLOWED_TYPES.includes(file.type)) {
    showMessage("Invalid file type. Please select a JPG or PNG image.", "error");
    return;
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    showMessage("File is too large. Max size is 5MB.", "error");
    return;
  }
  const formData = new FormData();
  formData.append("image", file);
  formData.append("config", JSON.stringify(currentConfig));
  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading & Analyzing...";
  aiStatusText.textContent = "Sending image to AI for extraction... this can take a few seconds.";
  try {
    const response = await fetch("http://127.0.0.1:5000/upload", {
      method: "POST",
       headers: {
    Authorization: `Bearer ${AUTH_TOKEN}`,
  },
      body: formData,
    });
    const result = await response.json();
    if (response.ok) {
      playSound("upload");
      showMessage(result.message, "success");
      renderExtraction(result.extraction, result.config);
    } else {
      showMessage(result.error || "Upload failed.", "error");
      aiStatusText.textContent = "No extraction — upload failed.";
    }
  } catch (err) {
    showMessage("Could not reach the server. Is the Flask backend running?", "error");
    aiStatusText.textContent = "No extraction — could not reach server.";
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload Attendance";
  }
});

// ---------- TABLE RENDERING ----------

function renderTableHeader() {
  resultsTableHead.innerHTML = "";
  const headerRow = document.createElement("tr");
  currentConfig.columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label;
    headerRow.appendChild(th);
  });
  for (let w = 1; w <= currentConfig.numWeeks; w++) {
    const th = document.createElement("th");
    th.textContent = `Wk${w}`;
    headerRow.appendChild(th);
  }
  headerRow.appendChild(document.createElement("th"));
  resultsTableHead.appendChild(headerRow);
}

function renderExtraction(extraction, configUsed) {
  if (!extraction.success) {
    aiStatusText.textContent = "⚠️ AI extraction failed: " + extraction.error;
    if (extraction.raw_text) {
      rawTextContent.textContent = extraction.raw_text;
      rawTextDetails.hidden = false;
    }
    return;
  }

  currentConfig = configUsed || currentConfig;
  const data = extraction.data;
  aiStatusText.textContent = "✅ Extraction complete. Review and correct every row below, then confirm.";
  reviewBanner.hidden = false;

  const studentCount = (data.students || []).length;
  sheetInfo.textContent = `Students detected: ${studentCount}`;

  renderTableHeader();
  resultsTableBody.innerHTML = "";
  (data.students || []).forEach((student) => addEditableRow(student));

  resultsTableWrapper.hidden = false;
  reviewControls.hidden = false;

  rawTextContent.textContent = extraction.raw_text;
  rawTextDetails.hidden = false;
}

function addEditableRow(studentData) {
  const row = document.createElement("tr");

  currentConfig.columns.forEach((col) => {
    const cell = document.createElement("td");
    const input = document.createElement("input");
    input.type = "text";
    input.value = studentData[col.id] || "";
    input.className = "row-input";
    input.dataset.columnId = col.id;
    cell.appendChild(input);
    row.appendChild(cell);
  });

  const weeklyAttendance = studentData.weekly_attendance || [];
  for (let week = 1; week <= currentConfig.numWeeks; week++) {
    const entry = weeklyAttendance.find((w) => w.week === week);
    let status = entry ? entry.status : "Unclear";
    if (status === "1") status = "Present";
    if (status === "0") status = "Absent";

    const cell = document.createElement("td");
    const select = document.createElement("select");
    select.className = "row-status-select";
    STATUS_OPTIONS.forEach((option) => {
      const optionEl = document.createElement("option");
      optionEl.value = option.value;
      optionEl.textContent = option.label;
      select.appendChild(optionEl);
    });
    select.value = STATUS_OPTIONS.some((o) => o.value === status) ? status : "Unclear";
    cell.appendChild(select);
    row.appendChild(cell);
  }

  const actionCell = document.createElement("td");
  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.textContent = "✕";
  removeBtn.className = "remove-row-btn";
  removeBtn.addEventListener("click", function () {
    const firstInput = row.querySelector("input");
    const identifier = (firstInput && firstInput.value) || "this student";
    const confirmed = window.confirm(`Remove ${identifier} from the list? This cannot be undone.`);
    if (confirmed) row.remove();
  });
  actionCell.appendChild(removeBtn);
  row.appendChild(actionCell);

  resultsTableBody.appendChild(row);
}

addRowBtn.addEventListener("click", function () {
  const blank = {};
  currentConfig.columns.forEach((c) => (blank[c.id] = ""));
  blank.weekly_attendance = [];
  if (resultsTableHead.innerHTML === "") renderTableHeader();
  addEditableRow(blank);
  resultsTableWrapper.hidden = false;
  reviewControls.hidden = false;
});

// ---------- VALIDATION / SUBMIT ----------

function resolveUnclearStatuses() {
  const unclearSelects = Array.from(resultsTableBody.querySelectorAll(".row-status-select"))
    .filter((select) => select.value === "Unclear");

  if (unclearSelects.length === 0) {
    return true;
  }

  const proceed = window.confirm(
    `${unclearSelects.length} week entr${unclearSelects.length === 1 ? "y is" : "ies are"} still marked "Unclear."\n\n` +
    `Click OK to automatically leave these blank and continue, or Cancel to go back and review them manually.`
  );

  if (!proceed) {
    return false;
  }

  unclearSelects.forEach((select) => {
    select.value = "";
  });

  return true;
}

function collectAndValidateStudents() {
  const rows = Array.from(resultsTableBody.querySelectorAll("tr"));
  const students = [];
  const errors = [];

  if (rows.length === 0) {
    errors.push("There are no students in the table. Add at least one row first.");
    return { students, errors };
  }

  rows.forEach((row, index) => {
    const rowNumber = index + 1;
    const student = {};
    currentConfig.columns.forEach((col) => {
      const input = row.querySelector(`input[data-column-id="${col.id}"]`);
      student[col.id] = input ? input.value.trim() : "";
    });

    const statusSelects = row.querySelectorAll(".row-status-select");
    const weeklyAttendance = [];
    statusSelects.forEach((select, weekIndex) => {
      const status = select.value;
      if (!VALID_FINAL_STATUSES.includes(status)) {
        errors.push(`Row ${rowNumber}, Week ${weekIndex + 1}: still marked "${status}" — please pick a real status.`);
      }
      weeklyAttendance.push({ week: weekIndex + 1, status: status });
    });
    student.weekly_attendance = weeklyAttendance;

    students.push(student);
  });

  return { students, errors };
}

confirmBtn.addEventListener("click", async function () {
  confirmMessage.hidden = true;

  if (!resolveUnclearStatuses()) return;

  const { students, errors } = collectAndValidateStudents();
  if (errors.length > 0) {
    showConfirmMessage("Please fix the following before confirming:\n" + errors.join("\n"), "error");
    return;
  }

  confirmBtn.disabled = true;
  confirmBtn.textContent = "Confirming...";

  try {
    const response = await fetch("http://127.0.0.1:5000/confirm-attendance", {
      method: "POST",
     headers: { "Content-Type": "application/json", Authorization: `Bearer ${AUTH_TOKEN}` },
      body: JSON.stringify({
        students: students,
        config: currentConfig,
        course_name: courseNameInput.value.trim(),
      }),
    });
    const result = await response.json();
    if (response.ok) {
      playSound("confirm");
      showConfirmMessage(result.message || "Attendance confirmed!", "success");
    } else {
      showConfirmMessage(result.error || "Could not confirm attendance.", "error");
    }
  } catch (err) {
    showConfirmMessage("Could not reach the server. Is the Flask backend running?", "error");
  } finally {
    confirmBtn.disabled = false;
    confirmBtn.textContent = "Confirm Attendance";
  }
});


downloadPdfBtn.addEventListener("click", async function () {
  confirmMessage.hidden = true;

  if (!resolveUnclearStatuses()) return;

  const { students, errors } = collectAndValidateStudents();
  if (errors.length > 0) {
    showConfirmMessage("Please fix the following before downloading:\n" + errors.join("\n"), "error");
    return;
  }

  downloadPdfBtn.disabled = true;
  downloadPdfBtn.textContent = "Generating PDF...";

  try {
    const response = await fetch("http://127.0.0.1:5000/export-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${AUTH_TOKEN}` },
      body: JSON.stringify({ students: students, config: currentConfig }),
    });
    if (!response.ok) {
      const result = await response.json();
      showConfirmMessage(result.error || "Could not generate PDF.", "error");
      return;
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "attendance_register.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    playSound("export");
    showConfirmMessage("PDF downloaded successfully.", "success");
  } catch (err) {
    showConfirmMessage("Could not reach the server. Is the Flask backend running?", "error");
  } finally {
    downloadPdfBtn.disabled = false;
    downloadPdfBtn.textContent = "Download as PDF";
  }
});
downloadExcelBtn.addEventListener("click", async function () {
  confirmMessage.hidden = true;

  if (!resolveUnclearStatuses()) return;

  const { students, errors } = collectAndValidateStudents();
  if (errors.length > 0) {
    showConfirmMessage("Please fix the following before downloading:\n" + errors.join("\n"), "error");
    return;
  }

  downloadExcelBtn.disabled = true;
  downloadExcelBtn.textContent = "Generating Excel...";

  try {
    const response = await fetch("http://127.0.0.1:5000/export-excel", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${AUTH_TOKEN}` },
      body: JSON.stringify({ students: students, config: currentConfig }),
    });
    if (!response.ok) {
      const result = await response.json();
      showConfirmMessage(result.error || "Could not generate Excel file.", "error");
      return;
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "attendance_register.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    showConfirmMessage("Excel file downloaded successfully.", "success");
  } catch (err) {
    showConfirmMessage("Could not reach the server. Is the Flask backend running?", "error");
  } finally {
    downloadExcelBtn.disabled = false;
    downloadExcelBtn.textContent = "Download as Excel";
  }
});

// ---------- PDF IMPORT ----------

importPdfBtn.addEventListener("click", async function () {
  clearMessage();
  const file = pdfInput.files[0];
  if (!file) {
    showMessage("Please choose a PDF file first.", "error");
    return;
  }
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showMessage("Please choose a valid .pdf file.", "error");
    return;
  }
  const formData = new FormData();
  formData.append("pdf", file);
  importPdfBtn.disabled = true;
  importPdfBtn.textContent = "Loading PDF...";
  try {
    const response = await fetch("http://127.0.0.1:5000/import-pdf", {
      method: "POST",
      headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      body: formData,
    });
    const result = await response.json();
    if (response.ok && result.success) {
      loadStudentsIntoTable(result.data.students || [], result.data.config);
      showMessage("PDF loaded. You can continue editing below.", "success");
    } else {
      showMessage(result.error || "Could not load this PDF.", "error");
    }
  } catch (err) {
    showMessage("Could not reach the server. Is the Flask backend running?", "error");
  } finally {
    importPdfBtn.disabled = false;
    importPdfBtn.textContent = "Load PDF";
  }
});

function loadStudentsIntoTable(students, config) {
  if (config) {
    applyConfig(config);
  }
  resetAiSection();
  aiStatusText.textContent = "Loaded from a previously downloaded PDF — already reviewed once, but please check before confirming again.";
  reviewBanner.hidden = false;
  sheetInfo.textContent = `Students loaded: ${students.length}`;
  renderTableHeader();
  resultsTableBody.innerHTML = "";
  students.forEach((student) => addEditableRow(student));
  resultsTableWrapper.hidden = false;
  reviewControls.hidden = false;
}

// ---------- HELPERS ----------

function showConfirmMessage(text, type) {
  confirmMessage.textContent = text;
  confirmMessage.className = "message " + type;
  confirmMessage.hidden = false;
}

function resetAiSection() {
  aiStatusText.textContent = "No extraction yet — upload an image above.";
  reviewBanner.hidden = true;
  sheetInfo.textContent = "";
  resultsTableBody.innerHTML = "";
  resultsTableWrapper.hidden = true;
  reviewControls.hidden = true;
  confirmMessage.hidden = true;
  rawTextDetails.hidden = true;
  rawTextContent.textContent = "";
}

function showMessage(text, type) {
  messageBox.textContent = text;
  messageBox.className = "message " + type;
  messageBox.hidden = false;
}

function clearMessage() {
  messageBox.hidden = true;
  messageBox.textContent = "";
}

// ===== Background & Sound Settings =====

const bgSlideshow = document.getElementById("bgSlideshow");
const customBgLayer = document.getElementById("customBgLayer");
const bgSourceDefault = document.getElementById("bgSourceDefault");
const bgSourceCustom = document.getElementById("bgSourceCustom");
const customBgControls = document.getElementById("customBgControls");
const customBgInput = document.getElementById("customBgInput");
const removeCustomBgBtn = document.getElementById("removeCustomBgBtn");
const slideshowToggle = document.getElementById("slideshowToggle");
const soundToggle = document.getElementById("soundToggle");

const BG_SETTINGS_KEY = "snapattend_bg_settings";

function loadBgSettings() {
  const saved = localStorage.getItem(BG_SETTINGS_KEY);
  if (!saved) {
    return { source: "default", slideshowEnabled: true, soundEnabled: false, customImage: null };
  }
  try {
    return JSON.parse(saved);
  } catch (e) {
    return { source: "default", slideshowEnabled: true, soundEnabled: false, customImage: null };
  }
}

function saveBgSettings(settings) {
  localStorage.setItem(BG_SETTINGS_KEY, JSON.stringify(settings));
}

function applyBgSettings(settings) {
  if (settings.source === "custom" && settings.customImage) {
    bgSlideshow.hidden = true;
    customBgLayer.hidden = false;
    customBgLayer.style.backgroundImage = `url(${settings.customImage})`;
    bgSourceCustom.checked = true;
    customBgControls.hidden = false;
  } else {
    bgSlideshow.hidden = false;
    customBgLayer.hidden = true;
    bgSourceDefault.checked = true;
    customBgControls.hidden = true;
  }

  if (settings.slideshowEnabled) {
    bgSlideshow.classList.remove("paused");
  } else {
    bgSlideshow.classList.add("paused");
  }
  slideshowToggle.checked = settings.slideshowEnabled;
  soundToggle.checked = settings.soundEnabled;
}

bgSourceDefault.addEventListener("change", function () {
  const settings = loadBgSettings();
  settings.source = "default";
  saveBgSettings(settings);
  applyBgSettings(settings);
});

bgSourceCustom.addEventListener("change", function () {
  const settings = loadBgSettings();
  if (!settings.customImage) {
    alert("Please choose an image file first using the box below.");
    bgSourceDefault.checked = true;
    return;
  }
  settings.source = "custom";
  saveBgSettings(settings);
  applyBgSettings(settings);
});

customBgInput.addEventListener("change", function () {
  const file = customBgInput.files[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    alert("Please choose a valid image file.");
    return;
  }
  const reader = new FileReader();
  reader.onload = function (event) {
    const settings = loadBgSettings();
    settings.source = "custom";
    settings.customImage = event.target.result;
    saveBgSettings(settings);
    applyBgSettings(settings);
  };
  reader.readAsDataURL(file);
});

removeCustomBgBtn.addEventListener("click", function () {
  const settings = loadBgSettings();
  settings.source = "default";
  settings.customImage = null;
  saveBgSettings(settings);
  applyBgSettings(settings);
  customBgInput.value = "";
});

slideshowToggle.addEventListener("change", function () {
  const settings = loadBgSettings();
  settings.slideshowEnabled = slideshowToggle.checked;
  saveBgSettings(settings);
  applyBgSettings(settings);
});

soundToggle.addEventListener("change", function () {
  const settings = loadBgSettings();
  settings.soundEnabled = soundToggle.checked;
  saveBgSettings(settings);
});

function playSound(name) {
  const settings = loadBgSettings();
  if (!settings.soundEnabled) return;
  const audio = document.getElementById("sound-" + name);
  if (!audio) return;
  audio.currentTime = 0;
  audio.play().catch(() => {
    // Ignore errors - missing file or browser autoplay restriction
  });
}

// ---------- PAGE STARTUP ----------

document.addEventListener("DOMContentLoaded", function () {
  initConfig();
  applyBgSettings(loadBgSettings());
});
loggedInAs.textContent = `Logged in as: ${localStorage.getItem("snapattend_username") || "Unknown"}`;

logoutBtn.addEventListener("click", async function () {
  try {
    await fetch("http://127.0.0.1:5000/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
    });
  } catch (err) {
    // even if this fails, log out locally anyway
  }
  localStorage.removeItem("snapattend_token");
  localStorage.removeItem("snapattend_username");
  window.location.href = "auth.html";
});
// ---------- ATTENDANCE HISTORY ----------

async function loadHistory() {
  historyList.innerHTML = "Loading...";
  try {
const response = await fetch("http://127.0.0.1:5000/attendance-history", {
      headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
    });
    const result = await response.json();
    historyList.innerHTML = "";
    if (!result.sessions || result.sessions.length === 0) {
      historyList.textContent = "No confirmed attendance yet.";
      return;
    }
    result.sessions.forEach((session) => {
      const item = document.createElement("div");
      item.className = "history-item";
      const date = new Date(session.confirmed_at).toLocaleString();
      item.textContent = `${session.course_name} — ${date} — ${session.student_count} student(s)`;
      item.addEventListener("click", () => loadHistoryDetail(session.id));
      historyList.appendChild(item);
    });
  } catch (err) {
    historyList.textContent = "Could not reach the server.";
  }
}

async function loadHistoryDetail(sessionId) {
  try {
  const response = await fetch(`http://127.0.0.1:5000/attendance-history/${sessionId}`, {
      headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
    });
    const details = await response.json();
    if (!response.ok) {
      alert(details.error || "Could not load this session.");
      return;
    }

    historyDetailTitle.textContent = `${details.course_name} — ${new Date(details.confirmed_at).toLocaleString()}`;

    const config = details.config;
    historyDetailHead.innerHTML = "";
    const headerRow = document.createElement("tr");
    config.columns.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.label;
      headerRow.appendChild(th);
    });
    for (let w = 1; w <= config.numWeeks; w++) {
      const th = document.createElement("th");
      th.textContent = `Wk${w}`;
      headerRow.appendChild(th);
    }
    historyDetailHead.appendChild(headerRow);

    historyDetailBody.innerHTML = "";
    details.students.forEach((student) => {
      const row = document.createElement("tr");
      config.columns.forEach((col) => {
        const td = document.createElement("td");
        td.textContent = student[col.id] || "";
        row.appendChild(td);
      });
      const weeklyMap = {};
      (student.weekly_attendance || []).forEach((w) => (weeklyMap[w.week] = w.status));
      for (let w = 1; w <= config.numWeeks; w++) {
        const td = document.createElement("td");
        td.textContent = weeklyMap[w] || "";
        row.appendChild(td);
      }
      historyDetailBody.appendChild(row);
    });

    historyDetailWrapper.hidden = false;
  } catch (err) {
    alert("Could not reach the server.");
  }
}

loadHistoryBtn.addEventListener("click", loadHistory);
document.addEventListener("DOMContentLoaded", loadHistory); 