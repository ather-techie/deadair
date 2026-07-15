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
const progressList = document.getElementById("progress");
const resultDiv = document.getElementById("result");
const originalPreviewDiv = document.getElementById("original-preview");
const transcriptDiv = document.getElementById("transcript");
const cancelBtn = document.getElementById("cancel-btn");
const removeSilenceCheckbox = document.getElementById("remove-silence");
const removeFillerCheckbox = document.getElementById("remove-filler");
const showTranscriptCheckbox = document.getElementById("show-transcript");
const optionsError = document.getElementById("options-error");
const storageInfoDiv = document.getElementById("storage-info");

let pollTimeout = null;
let currentJobId = null;
let pollFailures = 0;
let wantTranscript = false;

let transcriptPollTimeout = null;
let transcriptPollFailures = 0;
let transcriptCursor = -1;

let originalObjectUrl = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = document.getElementById("video").files[0];
  if (!file) return;

  const removeSilence = removeSilenceCheckbox.checked;
  const removeFiller = removeFillerCheckbox.checked;
  const showTranscript = showTranscriptCheckbox.checked;
  optionsError.hidden = removeSilence || removeFiller || showTranscript;
  if (!removeSilence && !removeFiller && !showTranscript) return;

  const body = new FormData();
  body.append("video", file);
  body.append("remove_silence", removeSilence);
  body.append("remove_filler", removeFiller);
  body.append("show_transcript", showTranscript);

  wantTranscript = showTranscript;
  stopPolling();
  stopTranscriptPolling();
  progressList.innerHTML = "";
  resultDiv.innerHTML = "";
  transcriptDiv.innerHTML = "";
  transcriptDiv.hidden = true;
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
    if (wantTranscript) {
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
  transcriptDiv.hidden = false;
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

    transcriptDiv.appendChild(p);
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
  storageInfoDiv.hidden = false;
}

loadStorageInfo();
