const state = {
  provider: "runway",
  file: null,
  polling: null,
};

// ---------- Nav ----------

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`view-${btn.dataset.view}`).classList.add("active");
    if (btn.dataset.view === "history") loadHistory();
    if (btn.dataset.view === "settings") loadSettings();
  });
});

// ---------- Upload ----------

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const previewImg = document.getElementById("preview-img");
const dropzoneEmpty = document.getElementById("dropzone-empty");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});

function setFile(file) {
  state.file = file;
  const url = URL.createObjectURL(file);
  previewImg.src = url;
  previewImg.hidden = false;
  dropzoneEmpty.hidden = true;
  updateGenerateState();
}

// ---------- Motion presets ----------

document.querySelectorAll("#motion-presets .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.getElementById("motion-prompt").value = chip.dataset.prompt;
    updateGenerateState();
  });
});

document.getElementById("motion-prompt").addEventListener("input", updateGenerateState);

// ---------- Advanced / scene toggle ----------

const enhanceToggle = document.getElementById("enhance-toggle");
const scenePromptEl = document.getElementById("scene-prompt");
enhanceToggle.addEventListener("change", () => {
  scenePromptEl.disabled = !enhanceToggle.checked;
});

// ---------- Provider ----------

document.querySelectorAll(".provider-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".provider-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.provider = btn.dataset.provider;
  });
});

// ---------- Generate button state ----------

function updateGenerateState() {
  const hasFile = !!state.file;
  const hasPrompt = document.getElementById("motion-prompt").value.trim().length > 0;
  const btn = document.getElementById("generate-btn");
  const hint = document.getElementById("generate-hint");
  btn.disabled = !(hasFile && hasPrompt);
  hint.textContent = btn.disabled
    ? "Upload a photo and add a motion prompt to continue."
    : "";
}

// ---------- Generate ----------

document.getElementById("generate-btn").addEventListener("click", async () => {
  const form = new FormData();
  form.append("file", state.file);
  form.append("motion_prompt", document.getElementById("motion-prompt").value.trim());
  form.append("caption", document.getElementById("caption-input").value.trim());
  form.append("provider", state.provider);
  form.append("enhance_scene", enhanceToggle.checked);
  form.append("scene_prompt", scenePromptEl.value.trim());

  const resultPanel = document.getElementById("result-panel");
  resultPanel.hidden = false;
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  resetProgress();
  document.getElementById("generate-btn").disabled = true;

  let resp;
  try {
    resp = await fetch("/api/jobs", { method: "POST", body: form });
  } catch (err) {
    setProgressMessage("Network error: " + err.message, true);
    return;
  }

  const data = await resp.json();
  if (!resp.ok) {
    setProgressMessage(data.error || "Failed to start job", true);
    updateGenerateState();
    return;
  }

  pollJob(data.job_id);
});

function resetProgress() {
  document.querySelectorAll(".progress-step").forEach((el) => el.classList.remove("active", "done"));
  document.getElementById("progress-message").textContent = "";
  document.getElementById("result-video").hidden = true;
  document.getElementById("download-link").hidden = true;
}

function setProgressMessage(msg, isError) {
  const el = document.getElementById("progress-message");
  el.textContent = msg;
  el.style.color = isError ? "var(--danger)" : "";
}

const STEP_ORDER = ["removing_bg", "enhancing_scene", "animating", "captioning"];

function updateProgressUI(status, message) {
  const idx = STEP_ORDER.indexOf(status);
  document.querySelectorAll(".progress-step").forEach((el) => {
    const stepIdx = STEP_ORDER.indexOf(el.dataset.step);
    el.classList.remove("active", "done");
    if (status === "done") {
      el.classList.add("done");
    } else if (stepIdx < idx) {
      el.classList.add("done");
    } else if (stepIdx === idx) {
      el.classList.add("active");
    }
  });
  setProgressMessage(message, status === "error");
}

function pollJob(jobId) {
  if (state.polling) clearInterval(state.polling);
  state.polling = setInterval(async () => {
    const resp = await fetch(`/api/jobs/${jobId}`);
    const data = await resp.json();
    updateProgressUI(data.status, data.message);

    if (data.status === "done") {
      clearInterval(state.polling);
      const video = document.getElementById("result-video");
      const link = document.getElementById("download-link");
      video.src = data.video_url;
      video.hidden = false;
      link.href = data.video_url;
      link.hidden = false;
      document.getElementById("generate-btn").disabled = false;
    } else if (data.status === "error") {
      clearInterval(state.polling);
      document.getElementById("generate-btn").disabled = false;
    }
  }, 2000);
}

// ---------- History ----------

async function loadHistory() {
  const grid = document.getElementById("history-grid");
  grid.innerHTML = "";
  const resp = await fetch("/api/jobs");
  const jobs = await resp.json();

  if (!jobs.length) {
    grid.innerHTML = '<div class="history-empty">Nothing generated yet.</div>';
    return;
  }

  for (const job of jobs) {
    const card = document.createElement("div");
    card.className = "history-card";
    if (job.video_url) {
      card.innerHTML = `<video src="${job.video_url}" controls></video><div class="muted small">${job.status}</div>`;
    } else {
      card.innerHTML = `<div class="muted small">${job.id} — ${job.message || job.status}</div>`;
    }
    grid.appendChild(card);
  }
}

// ---------- Settings ----------

async function loadSettings() {
  const resp = await fetch("/api/settings");
  const data = await resp.json();

  const runwayEl = document.getElementById("runway-current");
  runwayEl.textContent = data.runway.configured
    ? `Current key: ${data.runway.masked}`
    : "No key set yet.";

  const klingEl = document.getElementById("kling-current");
  klingEl.textContent = data.kling.configured
    ? `Current key: ${data.kling.masked} (model: ${data.kling.model})`
    : "No key set yet.";
  document.getElementById("kling-model-input").value = data.kling.model || "kling-v2-5-turbo";

  updateSidebarKeyStatus(data);
}

function updateSidebarKeyStatus(data) {
  const dotWrap = document.getElementById("key-status");
  const text = document.getElementById("key-status-text");
  const hasAny = data.runway.configured || data.kling.configured;
  dotWrap.classList.toggle("ok", hasAny);
  if (hasAny) {
    const parts = [];
    if (data.runway.configured) parts.push("Runway");
    if (data.kling.configured) parts.push("Kling");
    text.textContent = parts.join(" + ") + " connected";
  } else {
    text.textContent = "No API key set";
  }
}

document.getElementById("save-runway").addEventListener("click", async () => {
  const key = document.getElementById("runway-key-input").value.trim();
  if (!key) return;
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runway_key: key }),
  });
  document.getElementById("runway-key-input").value = "";
  loadSettings();
});

document.getElementById("save-kling").addEventListener("click", async () => {
  const key = document.getElementById("kling-key-input").value.trim();
  const model = document.getElementById("kling-model-input").value.trim();
  if (!key && !model) return;
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kling_key: key || undefined, kling_model: model || undefined }),
  });
  document.getElementById("kling-key-input").value = "";
  loadSettings();
});

// ---------- Init ----------

loadSettings();
