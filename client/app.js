const UPLOAD_URL = "/api/videos";
const POLL_INTERVAL_MS = 1500;
const MAX_BACKOFF_MS = 15000;

const form = document.getElementById("upload-form");
const status = document.getElementById("status");
const progressList = document.getElementById("progress");
const resultDiv = document.getElementById("result");
const cancelBtn = document.getElementById("cancel-btn");

let pollTimeout = null;
let currentJobId = null;
let pollFailures = 0;

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = document.getElementById("video").files[0];
  if (!file) return;

  const body = new FormData();
  body.append("video", file);

  stopPolling();
  progressList.innerHTML = "";
  resultDiv.innerHTML = "";
  cancelBtn.hidden = true;
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

      if (job.status === "done") {
        finishPolling();
        setStatus("Done.");
        showResult(videoId);
      } else if (job.status === "failed" || job.status === "cancelled") {
        finishPolling();
        const failedStep = job.steps.find((s) => s.status === "failed");
        setStatus(
          failedStep ? `Failed at ${failedStep.step}: ${failedStep.error}` : `Job ${job.status}.`,
          job.status === "failed"
        );
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
  }, backoffDelay());
}

function backoffDelay() {
  if (pollFailures === 0) return POLL_INTERVAL_MS;
  return Math.min(POLL_INTERVAL_MS * 2 ** pollFailures, MAX_BACKOFF_MS);
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

    progressList.appendChild(li);
  }
}

function showResult(videoId) {
  resultDiv.innerHTML = "";
  const video = document.createElement("video");
  video.controls = true;
  video.src = `/api/videos/${videoId}/result`;
  resultDiv.appendChild(video);
}
