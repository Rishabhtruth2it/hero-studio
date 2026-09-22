const state = {
  provider: "runway",
  sceneEngine: "local",
  localSceneAvailable: true,
  file: null,
  polling: null,
  wizVibe: null,
  wizAction: null,
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
    if (btn.dataset.view === "admin") loadAdmin();
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
const sceneEngineRow = document.getElementById("scene-engine-row");
enhanceToggle.addEventListener("change", () => {
  scenePromptEl.disabled = !enhanceToggle.checked;
  sceneEngineRow.hidden = !enhanceToggle.checked;
});

document.querySelectorAll(".engine-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.disabled) return;
    document.querySelectorAll(".engine-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.sceneEngine = btn.dataset.engine;
  });
});

async function loadPlatform() {
  try {
    const resp = await fetch("/api/platform");
    const data = await resp.json();
    state.localSceneAvailable = data.local_scene_engine_available;
    const localBtn = document.querySelector('.engine-btn[data-engine="local"]');
    const openaiBtn = document.querySelector('.engine-btn[data-engine="openai"]');
    if (!data.local_scene_engine_available) {
      localBtn.disabled = true;
      localBtn.style.opacity = 0.4;
      localBtn.querySelector(".provider-sub").textContent = `Not available on ${data.os} — needs Apple Silicon`;
      document.querySelectorAll(".engine-btn").forEach((b) => b.classList.remove("active"));
      openaiBtn.classList.add("active");
      state.sceneEngine = "openai";
    }
  } catch (e) { /* platform check is best-effort */ }
}

// ---------- Provider ----------

document.querySelectorAll(".provider-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".provider-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.provider = btn.dataset.provider;
  });
});

// ---------- Wizard ----------

const wizardToggle = document.getElementById("wizard-toggle");
const wizardBody = document.getElementById("wizard-body");
wizardToggle.addEventListener("click", () => {
  const isOpen = !wizardBody.hidden;
  wizardBody.hidden = isOpen;
  wizardToggle.classList.toggle("open", !isOpen);
});

document.querySelectorAll("#wiz-vibe-chips .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll("#wiz-vibe-chips .chip").forEach((c) => c.classList.remove("selected"));
    chip.classList.add("selected");
    state.wizVibe = chip.dataset.value;
  });
});

document.querySelectorAll("#wiz-action-chips .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll("#wiz-action-chips .chip").forEach((c) => c.classList.remove("selected"));
    chip.classList.add("selected");
    state.wizAction = chip.dataset.value;
  });
});

document.getElementById("wizard-generate").addEventListener("click", async () => {
  const statusEl = document.getElementById("wizard-status");
  const product = document.getElementById("wiz-product").value.trim();
  const setting = document.getElementById("wiz-setting").value.trim();

  if (!product) {
    statusEl.textContent = "Tell us what the product is, at least.";
    statusEl.style.color = "var(--danger)";
    return;
  }

  statusEl.style.color = "";
  statusEl.textContent = "Writing your prompts...";

  const resp = await fetch("/api/prompt-helper", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      product,
      setting,
      vibe: state.wizVibe || "",
      action: state.wizAction || "",
    }),
  });
  const data = await resp.json();

  if (!resp.ok) {
    statusEl.textContent = data.error || "Couldn't generate prompts.";
    statusEl.style.color = "var(--danger)";
    return;
  }

  document.getElementById("motion-prompt").value = data.motion_prompt || "";
  if (data.caption) document.getElementById("caption-input").value = data.caption;

  if (data.scene_prompt && setting) {
    scenePromptEl.value = data.scene_prompt;
    enhanceToggle.checked = true;
    scenePromptEl.disabled = false;
    sceneEngineRow.hidden = false;
  }

  statusEl.style.color = "var(--success)";
  statusEl.textContent = "Done — prompts filled in below. Feel free to tweak them.";
  updateGenerateState();
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
  form.append("scene_engine", state.sceneEngine);

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

  const openaiEl = document.getElementById("openai-current");
  openaiEl.textContent = data.openai.configured
    ? `Current key: ${data.openai.masked} (model: ${data.openai.model})`
    : "No key set yet.";
  document.getElementById("openai-model-input").value = data.openai.model || "gpt-image-1-mini";

  const licenseEl = document.getElementById("license-current");
  licenseEl.textContent = data.license.configured
    ? `Current key: ${data.license.masked}`
    : "No license key set yet.";

  updateSidebarKeyStatus(data);
}

function updateSidebarKeyStatus(data) {
  const dotWrap = document.getElementById("key-status");
  const text = document.getElementById("key-status-text");
  const hasAny = data.runway.configured || data.kling.configured || data.openai.configured;
  dotWrap.classList.toggle("ok", hasAny);
  if (hasAny) {
    const parts = [];
    if (data.runway.configured) parts.push("Runway");
    if (data.kling.configured) parts.push("Kling");
    if (data.openai.configured) parts.push("OpenAI");
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

document.getElementById("save-openai").addEventListener("click", async () => {
  const key = document.getElementById("openai-key-input").value.trim();
  const model = document.getElementById("openai-model-input").value.trim();
  if (!key && !model) return;
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ openai_key: key || undefined, openai_model: model || undefined }),
  });
  document.getElementById("openai-key-input").value = "";
  loadSettings();
});

document.getElementById("save-license").addEventListener("click", async () => {
  const key = document.getElementById("license-key-input").value.trim();
  if (!key) return;
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ license_key: key }),
  });
  document.getElementById("license-key-input").value = "";
  loadSettings();
  checkLicense();
});

// ---------- License gate ----------

async function checkLicense() {
  const resp = await fetch("/api/license/status");
  const data = await resp.json();

  document.getElementById("machine-id-box").textContent = data.machine_id || "unavailable";
  document.getElementById("nav-admin").hidden = !data.is_admin;

  const overlay = document.getElementById("license-block");
  if (data.ok) {
    overlay.hidden = true;
  } else {
    overlay.hidden = false;
    document.getElementById("license-block-reason").textContent = data.reason;
  }
  return data;
}

document.getElementById("license-block-settings-btn").addEventListener("click", () => {
  document.getElementById("license-block").hidden = true;
  document.querySelector('.nav-item[data-view="settings"]').click();
});

// ---------- Admin ----------

async function loadAdmin() {
  const resp = await fetch("/api/admin/licenses");
  const data = await resp.json();
  if (!resp.ok) {
    document.getElementById("admin-licenses-body").innerHTML =
      `<tr><td colspan="4" class="muted small" style="color:var(--danger)">${data.error || "Couldn't load licenses."}</td></tr>`;
    return;
  }

  const killBtn = document.getElementById("kill-switch-btn");
  killBtn.classList.toggle("active", !!data.global_kill);
  killBtn.textContent = data.global_kill ? "Disable global kill switch" : "Enable global kill switch";

  const body = document.getElementById("admin-licenses-body");
  body.innerHTML = "";
  const licenses = data.licenses || {};
  const keys = Object.keys(licenses);

  if (!keys.length) {
    body.innerHTML = '<tr><td colspan="4" class="muted small">No licenses yet.</td></tr>';
    return;
  }

  for (const key of keys) {
    const lic = licenses[key];
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${lic.client || "—"}</td>
      <td><code>${key}</code>${lic.machine_id ? `<br><span class="muted small">🔒 ${lic.machine_id}</span>` : '<br><span class="muted small">unlocked</span>'}</td>
      <td><span class="status-pill ${lic.status}">${lic.status}</span></td>
      <td></td>
    `;
    const actionsCell = tr.querySelector("td:last-child");

    const toggleBtn = document.createElement("button");
    toggleBtn.textContent = lic.status === "active" ? "Revoke" : "Activate";
    toggleBtn.addEventListener("click", async () => {
      await fetch("/api/admin/licenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: lic.status === "active" ? "revoke" : "activate", key }),
      });
      loadAdmin();
    });
    actionsCell.appendChild(toggleBtn);

    if (!lic.machine_id) {
      const lockBtn = document.createElement("button");
      lockBtn.textContent = "Lock to a device";
      lockBtn.addEventListener("click", async () => {
        const machineId = prompt("Paste the Machine ID the client sent you:");
        if (!machineId) return;
        await fetch("/api/admin/licenses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "bind_machine", key, machine_id: machineId.trim() }),
        });
        loadAdmin();
      });
      actionsCell.appendChild(lockBtn);
    } else {
      const unlockBtn = document.createElement("button");
      unlockBtn.textContent = "Unlock";
      unlockBtn.addEventListener("click", async () => {
        await fetch("/api/admin/licenses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "bind_machine", key, machine_id: "" }),
        });
        loadAdmin();
      });
      actionsCell.appendChild(unlockBtn);
    }

    body.appendChild(tr);
  }
}

document.getElementById("admin-add-license").addEventListener("click", async () => {
  const client = document.getElementById("admin-new-client").value.trim();
  let key = document.getElementById("admin-new-key").value.trim();
  const machineId = document.getElementById("admin-new-machine").value.trim();
  if (!client) { alert("Client name is required."); return; }
  if (!key) key = crypto.randomUUID().replace(/-/g, "").slice(0, 20).toUpperCase();

  await fetch("/api/admin/licenses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "add", key, client, machine_id: machineId }),
  });
  document.getElementById("admin-new-client").value = "";
  document.getElementById("admin-new-key").value = "";
  document.getElementById("admin-new-machine").value = "";
  loadAdmin();
});

document.getElementById("kill-switch-btn").addEventListener("click", async () => {
  const enabling = !document.getElementById("kill-switch-btn").classList.contains("active");
  if (enabling && !confirm("This blocks EVERY non-admin install immediately. Continue?")) return;
  await fetch("/api/admin/licenses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "global_kill", enabled: enabling }),
  });
  loadAdmin();
});

// ---------- Updates ----------

async function checkForUpdate() {
  try {
    const resp = await fetch("/api/update/check");
    const data = await resp.json();
    const banner = document.getElementById("update-banner");
    if (data.update_available) {
      document.getElementById("update-banner-text").textContent =
        `A new version of Hero Studio is available (${data.commits_behind} update${data.commits_behind === 1 ? "" : "s"} behind).`;
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }
  } catch (e) { /* best-effort */ }
}

document.getElementById("update-banner-btn").addEventListener("click", async () => {
  const btn = document.getElementById("update-banner-btn");
  btn.disabled = true;
  btn.textContent = "Updating...";
  const resp = await fetch("/api/update/apply", { method: "POST" });
  const data = await resp.json();
  if (data.ok) {
    document.getElementById("update-banner-text").textContent =
      "Updated! Quit and reopen Hero Studio (re-run the launcher) to finish.";
    btn.hidden = true;
  } else {
    document.getElementById("update-banner-text").textContent = "Update failed: " + (data.error || "unknown error");
    btn.disabled = false;
    btn.textContent = "Retry";
  }
});

// ---------- Init ----------

loadSettings();
loadPlatform();
checkLicense();
checkForUpdate();
