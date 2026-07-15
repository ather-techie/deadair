const THEME_STORAGE_KEY = "deadair.theme";

(function initTheme() {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  const theme = stored || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = theme;
})();

const UPLOAD_URL = "/api/videos";
const POLL_INTERVAL_MS = 1500;
const MAX_BACKOFF_MS = 15000;
const STORAGE_PATHS_URL = "/api/system/storage-paths";
const STORAGE_PATHS_CACHE_KEY = "deadair.storagePaths";
const STORAGE_PATH_LABELS = {
  data_dir: "Data dir",
  uploads_dir: "Uploads",
  audio_dir: "Audio",
  artifacts_dir: "Artifacts",
  render_work_dir: "Render work",
  renders_dir: "Renders",
  sqlite_db_path: "Database",
  log_dir: "Logs",
};

const form = document.getElementById("upload-form");
const status = document.getElementById("status");
const totalTimeEl = document.getElementById("total-time");
const progressList = document.getElementById("progress");
const resultDiv = document.getElementById("result");
const originalPreviewDiv = document.getElementById("original-preview");
const originalTranscriptDiv = document.getElementById("original-transcript");
const originalTranscriptContentDiv = document.getElementById("original-transcript-content");
const resultTranscriptDiv = document.getElementById("result-transcript");
const resultTranscriptContentDiv = document.getElementById("result-transcript-content");
const cancelBtn = document.getElementById("cancel-btn");
const resetBtn = document.getElementById("reset-btn");
const removeSilenceCheckbox = document.getElementById("remove-silence");
const removeFillerCheckbox = document.getElementById("remove-filler");
const speedUpCutsCheckbox = document.getElementById("speed-up-cuts");
const speedMultiplierSelect = document.getElementById("speed-multiplier");
const showOriginalTranscriptCheckbox = document.getElementById("show-original-transcript");
const showResultTranscriptCheckbox = document.getElementById("show-result-transcript");
const optionsError = document.getElementById("options-error");
const storageInfoDiv = document.getElementById("storage-info");
const storageDetails = document.getElementById("storage-details");
const themeToggleBtn = document.getElementById("theme-toggle");
const themeToggleIcon = document.getElementById("theme-toggle-icon");

let pollTimeout = null;
let currentJobId = null;
let pollFailures = 0;
let wantOriginalTranscript = false;
let wantResultTranscript = false;
let resultTranscriptFetched = false;

let transcriptPollTimeout = null;
let transcriptPollFailures = 0;
let transcriptCursor = -1;

let originalObjectUrl = null;

function syncThemeIcon() {
  themeToggleIcon.textContent = document.documentElement.dataset.theme === "dark" ? "☀" : "☽";
}

themeToggleBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem(THEME_STORAGE_KEY, next);
  syncThemeIcon();
});

syncThemeIcon();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = document.getElementById("video").files[0];
  if (!file) return;

  const removeSilence = removeSilenceCheckbox.checked;
  const removeFiller = removeFillerCheckbox.checked;
  const speedUpCuts = speedUpCutsCheckbox.checked;
  const speedMultiplier = speedMultiplierSelect.value;
  const showOriginalTranscript = showOriginalTranscriptCheckbox.checked;
  const showResultTranscript = showResultTranscriptCheckbox.checked;
  const anyOptionSelected = removeSilence || removeFiller || showOriginalTranscript || showResultTranscript;
  optionsError.textContent = "Select at least one option.";
  optionsError.hidden = anyOptionSelected;
  if (!anyOptionSelected) return;
  if (speedUpCuts && !(removeSilence || removeFiller)) {
    optionsError.textContent = "Speed up instead of cut requires remove silence or remove filler words.";
    optionsError.hidden = false;
    return;
  }

  const body = new FormData();
  body.append("video", file);
  body.append("remove_silence", removeSilence);
  body.append("remove_filler", removeFiller);
  body.append("speed_up_cuts", speedUpCuts);
  body.append("speed_multiplier", speedMultiplier);
  body.append("show_original_transcript", showOriginalTranscript);
  body.append("show_result_transcript", showResultTranscript);

  wantOriginalTranscript = showOriginalTranscript;
  wantResultTranscript = showResultTranscript;
  resultTranscriptFetched = false;
  stopPolling();
  stopTranscriptPolling();
  progressList.innerHTML = "";
  totalTimeEl.textContent = "";
  resultDiv.innerHTML = "";
  originalTranscriptDiv.innerHTML = "";
  originalTranscriptContentDiv.hidden = true;
  resultTranscriptDiv.innerHTML = "";
  resultTranscriptContentDiv.hidden = true;
  cancelBtn.hidden = true;
  showOriginalPreview(file);
  setStatus(`Uploading ${file.name}...`);

  try {
    const response = await fetch(UPLOAD_URL, { method: "POST", body });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const { video_id: videoId, job_id: jobId } = await response.json();
    setStatus("Uploaded. Processing...");
    currentJobId = jobId;
    cancelBtn.hidden = false;
    pollFailures = 0;
    pollJob(videoId, jobId);
    if (wantOriginalTranscript) {
      transcriptCursor = -1;
      transcriptPollFailures = 0;
      pollTranscript(videoId);
    }
  } catch (err) {
    console.error("Upload failed:", err);
    setStatus("Upload failed — is the backend running?", true);
  }
});

cancelBtn.addEventListener("click", async () => {
  if (!currentJobId) return;
  cancelBtn.disabled = true;
  try {
    const response = await fetch(`/api/jobs/${currentJobId}/cancel`, { method: "POST" });
    if (!response.ok && response.status !== 409) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
  } catch (err) {
    console.error("Cancel failed:", err);
  } finally {
    cancelBtn.disabled = false;
  }
});

resetBtn.addEventListener("click", () => {
  if (currentJobId) {
    fetch(`/api/jobs/${currentJobId}/cancel`, { method: "POST" }).catch((err) => {
      console.error("Cancel on reset failed:", err);
    });
  }
  stopPolling();
  stopTranscriptPolling();
  currentJobId = null;
  pollFailures = 0;
  transcriptPollFailures = 0;
  transcriptCursor = -1;
  wantOriginalTranscript = false;
  wantResultTranscript = false;
  resultTranscriptFetched = false;

  form.reset();
  optionsError.hidden = true;
  progressList.innerHTML = "";
  totalTimeEl.textContent = "";
  resultDiv.innerHTML = "";
  originalTranscriptDiv.innerHTML = "";
  originalTranscriptContentDiv.hidden = true;
  resultTranscriptDiv.innerHTML = "";
  resultTranscriptContentDiv.hidden = true;
  if (originalObjectUrl) {
    URL.revokeObjectURL(originalObjectUrl);
    originalObjectUrl = null;
  }
  originalPreviewDiv.innerHTML = "";
  cancelBtn.hidden = true;
  setStatus("");
});

function pollJob(videoId, jobId) {
  pollTimeout = setTimeout(async () => {
    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const job = await response.json();
      pollFailures = 0;
      renderProgress(job);
      // Checked every tick (not just once the whole job is "done") so a
      // render that finishes before some other step fails still shows up.
      maybeShowResult(videoId, job);
      maybeShowResultTranscript(videoId, job);

      if (job.status === "done" || job.status === "failed" || job.status === "cancelled") {
        finishPolling();
        if (job.status === "done") {
          setStatus("Done.");
        } else {
          const failedStep = job.steps.find((s) => s.status === "failed");
          setStatus(
            failedStep ? `Failed at ${failedStep.step}: ${failedStep.error}` : `Job ${job.status}.`,
            job.status === "failed"
          );
        }
      } else {
        setStatus(job.status === "running" ? "Processing..." : "Waiting to start...");
        pollJob(videoId, jobId);
      }
    } catch (err) {
      pollFailures += 1;
      console.error("Poll failed:", err);
      setStatus(`Lost connection to backend, retrying… (attempt ${pollFailures})`, true);
      pollJob(videoId, jobId);
    }
  }, backoffDelay(pollFailures));
}

function maybeShowResult(videoId, job) {
  if (resultDiv.childElementCount > 0) return;
  const renderStep = job.steps.find((s) => s.step === "render");
  if (renderStep && (renderStep.status === "done" || renderStep.status === "skipped_cached")) {
    showResult(videoId);
  }
}

// The result transcript needs the finished EDL (build_edl), which has no
// incremental/partial form -- unlike the original transcript it's fetched
// once, in full, rather than polled.
function maybeShowResultTranscript(videoId, job) {
  if (!wantResultTranscript || resultTranscriptFetched) return;
  const buildEdlStep = job.steps.find((s) => s.step === "build_edl");
  if (!buildEdlStep || !(buildEdlStep.status === "done" || buildEdlStep.status === "skipped_cached")) return;

  resultTranscriptFetched = true;
  fetch(`/api/videos/${videoId}/transcript/result`)
    .then((response) => {
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    })
    .then((data) => {
      resultTranscriptContentDiv.hidden = false;
      renderResultTranscript(data.segments);
    })
    .catch((err) => {
      console.error("Result transcript fetch failed:", err);
      resultTranscriptFetched = false;
    });
}

function backoffDelay(failures) {
  if (failures === 0) return POLL_INTERVAL_MS;
  return Math.min(POLL_INTERVAL_MS * 2 ** failures, MAX_BACKOFF_MS);
}

function finishPolling() {
  stopPolling();
  currentJobId = null;
  cancelBtn.hidden = true;
}

function stopPolling() {
  clearTimeout(pollTimeout);
  pollTimeout = null;
}

function stopTranscriptPolling() {
  clearTimeout(transcriptPollTimeout);
  transcriptPollTimeout = null;
}

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${String(secs).padStart(2, "0")}s`;
}

function stepDurationSeconds(step) {
  if (!step.started_at) return null;
  const start = new Date(step.started_at).getTime();
  const end = step.finished_at ? new Date(step.finished_at).getTime() : Date.now();
  return (end - start) / 1000;
}

function renderProgress(job) {
  progressList.innerHTML = "";
  for (const step of job.steps) {
    const li = document.createElement("li");
    li.className = `step step-${step.status}`;

    const pct = Math.round(step.progress * 100);
    const label = document.createElement("span");
    label.className = "step-label";
    label.textContent = `${step.step} — ${step.status} (${pct}%)`;
    li.appendChild(label);

    const bar = document.createElement("div");
    bar.className = "step-bar";
    const fill = document.createElement("div");
    fill.className = "step-bar-fill";
    fill.style.width = `${pct}%`;
    bar.appendChild(fill);
    li.appendChild(bar);

    const durationSeconds = stepDurationSeconds(step);
    if (durationSeconds !== null) {
      const durationText = document.createElement("span");
      durationText.className = "step-duration";
      durationText.textContent = formatDuration(durationSeconds);
      li.appendChild(durationText);
    }

    if (step.error) {
      const errorText = document.createElement("span");
      errorText.className = "step-error";
      errorText.textContent = step.error;
      li.appendChild(errorText);
    }

    if (step.findings) {
      const findingsText = document.createElement("span");
      findingsText.className = "step-findings";
      const seconds = step.findings.seconds_removed.toFixed(1);
      findingsText.textContent = `${step.findings.cuts} cuts, ${seconds}s removed`;
      li.appendChild(findingsText);
    }

    progressList.appendChild(li);
  }

  const totalSeconds = (
    (job.status === "done" || job.status === "failed" || job.status === "cancelled"
      ? new Date(job.updated_at).getTime()
      : Date.now()) - new Date(job.created_at).getTime()
  ) / 1000;
  totalTimeEl.textContent = `Total: ${formatDuration(totalSeconds)}`;
}

function showOriginalPreview(file) {
  if (originalObjectUrl) URL.revokeObjectURL(originalObjectUrl);
  originalObjectUrl = URL.createObjectURL(file);

  originalPreviewDiv.innerHTML = "";
  const video = document.createElement("video");
  video.controls = true;
  video.src = originalObjectUrl;
  originalPreviewDiv.appendChild(video);
}

function showResult(videoId) {
  resultDiv.innerHTML = "";
  const video = document.createElement("video");
  video.controls = true;
  video.src = `/api/videos/${videoId}/result`;
  resultDiv.appendChild(video);
}

// Polls independently of pollJob/showResult, starting as soon as the upload
// finishes (not gated on job or render completion), so segments appear as
// Whisper produces them instead of waiting for the whole transcript -- or
// the whole job -- to finish.
function pollTranscript(videoId) {
  transcriptPollTimeout = setTimeout(async () => {
    try {
      const response = await fetch(`/api/videos/${videoId}/transcript/partial?after=${transcriptCursor}`);
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      transcriptPollFailures = 0;
      const partial = await response.json();
      appendTranscriptSegments(partial.segments);
      transcriptCursor = partial.next_after;
      if (!partial.finished) pollTranscript(videoId);
    } catch (err) {
      transcriptPollFailures += 1;
      console.error("Transcript poll failed:", err);
      pollTranscript(videoId);
    }
  }, backoffDelay(transcriptPollFailures));
}

function appendTranscriptSegments(segments) {
  if (!segments.length) return;
  originalTranscriptContentDiv.hidden = false;
  for (const segment of segments) {
    const p = document.createElement("p");
    p.className = "transcript-segment";

    const timestamp = document.createElement("span");
    timestamp.className = "transcript-timestamp";
    timestamp.textContent = formatTimestamp(segment.start);
    p.appendChild(timestamp);

    const text = document.createElement("span");
    text.className = "transcript-text";
    text.textContent = segment.text;
    p.appendChild(text);

    originalTranscriptDiv.appendChild(p);
  }
}

function renderResultTranscript(segments) {
  resultTranscriptDiv.innerHTML = "";
  if (!segments.length) {
    const empty = document.createElement("p");
    empty.className = "transcript-empty";
    empty.textContent = "Nothing survived the cuts.";
    resultTranscriptDiv.appendChild(empty);
    return;
  }

  for (const segment of segments) {
    const p = document.createElement("p");
    p.className = "transcript-segment";

    const pair = document.createElement("span");
    pair.className = "transcript-timestamp-pair";

    const originalTimestamp = document.createElement("span");
    originalTimestamp.className = "transcript-timestamp";
    originalTimestamp.textContent = formatTimestamp(segment.original_start);
    pair.appendChild(originalTimestamp);

    const arrow = document.createElement("span");
    arrow.className = "transcript-timestamp-arrow";
    arrow.textContent = "→";
    pair.appendChild(arrow);

    const resultTimestamp = document.createElement("span");
    resultTimestamp.className = "transcript-timestamp";
    resultTimestamp.textContent = formatTimestamp(segment.result_start);
    pair.appendChild(resultTimestamp);

    p.appendChild(pair);

    const text = document.createElement("span");
    text.className = "transcript-text";
    text.textContent = segment.text;
    p.appendChild(text);

    resultTranscriptDiv.appendChild(p);
  }
}

function formatTimestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

async function loadStorageInfo() {
  try {
    const response = await fetch(STORAGE_PATHS_URL);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const paths = await response.json();
    localStorage.setItem(STORAGE_PATHS_CACHE_KEY, JSON.stringify(paths));
    renderStorageInfo(paths, false);
  } catch (err) {
    console.error("Loading storage paths failed:", err);
    const cached = localStorage.getItem(STORAGE_PATHS_CACHE_KEY);
    if (cached) renderStorageInfo(JSON.parse(cached), true);
  }
}

function renderStorageInfo(paths, isCached) {
  storageInfoDiv.innerHTML = "";
  for (const [key, label] of Object.entries(STORAGE_PATH_LABELS)) {
    if (!(key in paths)) continue;
    const p = document.createElement("p");
    p.textContent = `${label}: ${paths[key]}`;
    storageInfoDiv.appendChild(p);
  }
  if (isCached) {
    const note = document.createElement("p");
    note.className = "storage-info-note";
    note.textContent = "(cached, may be stale — backend unreachable)";
    storageInfoDiv.appendChild(note);
  }
  storageDetails.hidden = false;
}

loadStorageInfo();
