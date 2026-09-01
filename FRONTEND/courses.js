const TOKEN = localStorage.getItem("snapattend_token");
const API = "http://127.0.0.1:5000";

async function apiCall(path, options = {}) {
  options.headers = { ...(options.headers || {}), Authorization: `Bearer ${TOKEN}` };
  const res = await fetch(API + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadCourses() {
  const list = document.getElementById("coursesList");
  list.innerHTML = "Loading...";
  try {
    const { courses } = await apiCall("/courses");
    if (courses.length === 0) {
      list.innerHTML = "<p>No courses yet. Add one above.</p>";
      return;
    }
    list.innerHTML = "";
    for (const course of courses) {
      const div = document.createElement("div");
      div.className = "glass-panel";
      div.style.padding = "1rem";
      div.style.marginBottom = "1rem";
      div.innerHTML = `
        <strong>${course.course_code || ""} ${course.course_name}</strong>
        <button data-id="${course.id}" class="editCourseBtn">Edit</button>
        <button data-id="${course.id}" class="deleteCourseBtn">Delete</button>
        <div class="topicsWrapper" data-course-id="${course.id}">
          <p>Loading topics...</p>
        </div>
        <input type="text" placeholder="Week (e.g. Week 1)" class="row-input newTopicWeek" data-course-id="${course.id}" style="width:100px;">
        <input type="text" placeholder="Topic title" class="row-input newTopicTitle" data-course-id="${course.id}" style="width:200px;">
        <textarea placeholder="Description (optional)" class="row-input newTopicDesc" data-course-id="${course.id}"></textarea>
        <button class="addTopicBtn" data-course-id="${course.id}">+ Add Topic</button>
      `;
      list.appendChild(div);
      loadTopics(course.id);
    }
    attachCourseHandlers();
  } catch (err) {
    list.textContent = "Error: " + err.message;
  }
}

async function loadTopics(courseId) {
  const wrapper = document.querySelector(`.topicsWrapper[data-course-id="${courseId}"]`);
  try {
    const { topics } = await apiCall(`/courses/${courseId}/topics`);
    if (topics.length === 0) {
      wrapper.innerHTML = "<p><em>No topics yet.</em></p>";
      return;
    }
    wrapper.innerHTML = topics.map(t => `
      <div style="border-top:1px solid #e5e7eb; padding:0.5rem 0;">
        <label>
          <input type="checkbox" class="studiedCheck" data-topic-id="${t.id}" ${t.studied ? "checked" : ""}>
          <strong>${t.week_label || ""} — ${t.title}</strong>
        </label>
        <p>${t.description || ""}</p>
        <button class="deleteTopicBtn" data-topic-id="${t.id}">Delete Topic</button>
      </div>
    `).join("");
    wrapper.querySelectorAll(".studiedCheck").forEach(cb => {
      cb.addEventListener("change", async () => {
        await apiCall(`/topics/${cb.dataset.topicId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ studied: cb.checked, title: "", week_label: "", description: "", materials: "" }),
        }).catch(() => {});
      });
    });
    wrapper.querySelectorAll(".deleteTopicBtn").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this topic?")) return;
        await apiCall(`/topics/${btn.dataset.topicId}`, { method: "DELETE" });
        loadTopics(courseId);
      });
    });
  } catch (err) {
    wrapper.textContent = "Error loading topics.";
  }
}

function attachCourseHandlers() {
  document.querySelectorAll(".deleteCourseBtn").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this course and all its topics?")) return;
      await apiCall(`/courses/${btn.dataset.id}`, { method: "DELETE" });
      loadCourses();
    });
  });
  document.querySelectorAll(".addTopicBtn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const courseId = btn.dataset.courseId;
      const week = document.querySelector(`.newTopicWeek[data-course-id="${courseId}"]`).value.trim();
      const title = document.querySelector(`.newTopicTitle[data-course-id="${courseId}"]`).value.trim();
      const desc = document.querySelector(`.newTopicDesc[data-course-id="${courseId}"]`).value.trim();
      if (!title) return alert("Topic title is required.");
      await apiCall(`/courses/${courseId}/topics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ week_label: week, title, description: desc }),
      });
      loadTopics(courseId);
    });
  });
}

document.getElementById("addCourseBtn").addEventListener("click", async () => {
  const name = document.getElementById("newCourseName").value.trim();
  const code = document.getElementById("newCourseCode").value.trim();
  if (!name) return alert("Course name is required.");
  await apiCall("/courses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ course_name: name, course_code: code }),
  });
  document.getElementById("newCourseName").value = "";
  document.getElementById("newCourseCode").value = "";
  loadCourses();
});

loadCourses();