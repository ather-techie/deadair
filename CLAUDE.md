# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

deadair is an automated video-editing pipeline: upload a video, extract audio, transcribe it, detect
silence and filler words, build an EDL (edit decision list), and render the cut. It's a monorepo with:

- `server/` — Python (FastAPI) backend, built as a strict hexagonal / ports-and-adapters architecture.
  This is where nearly all real logic lives.
- `client/` — a static HTML/JS upload page (`index.html`, `app.js`, `style.css`), no build step. It's a
  UI scaffold that polls `/api/jobs/{id}` and plays back `/api/videos/{id}/result`. No framework, no bundler.

As of M6, every port has a real adapter and the milestone build is complete: `build_container()` wires
`FfmpegAudioExtractor`, `FfmpegSilenceDetector`, `FasterWhisperTranscriber`, `FfmpegVideoRenderer`,
`RQJobRunner`, and `SqliteProgressReporter`. Job execution is now genuinely asynchronous — uploading a
video enqueues a real RQ job; nothing runs until a separate `python -m deadair.worker` process picks it
up (see Commands below for the full run sequence). The `infrastructure/media/fake_*.py` and
`InMemoryJobRunner`/`InMemoryProgressReporter` adapters still exist and are used by fast/isolated tests,
but are no longer wired into `build_container()`.

## Commands

All backend commands run from `server/`:

```
cd server
pip install -e ".[dev]"       # install package + pytest/hypothesis/httpx
pytest -q                     # run the full test suite
pytest tests/unit/domain/test_edl_builder.py -q     # run a single test file
pytest tests/unit/domain/test_edl_builder.py::test_name -q   # run a single test
pytest -m "not slow" -q       # skip tests requiring ffmpeg/faster-whisper/redis + real media fixtures
```

The server requires `DEADAIR_FFMPEG_BINARY_PATH` (env var, prefix `DEADAIR_`) to construct `Settings`.
Fast tests use a manually-built all-fake `Container` (see `tests/unit/presentation/conftest.py`) with a
placeholder, non-existent ffmpeg path — no real ffmpeg/whisper model needed. Only tests marked `slow`
(the ffmpeg- and faster-whisper-backed adapter tests under `tests/infrastructure/media/`) invoke real
binaries/models, resolved via `shutil.which("ffmpeg")` (skips if missing) or a `tiny` Whisper model
(downloaded on first run, then cached under `~/.cache/huggingface`), and are skipped by default
(`addopts = "-m 'not slow'"` in `pyproject.toml`). Run them explicitly with `pytest -m slow`.

Full local run sequence (see root `README.md`):
```
docker compose up -d redis                          # or a native redis-server on the same port
cd server
uvicorn deadair.presentation.main:app --reload       # terminal 1: API
python -m deadair.worker                             # terminal 2: worker -- required for jobs to progress
cd ../client && python -m http.server                # terminal 3: static client
```
Uploading via the client just hits `/api/videos`/`/api/jobs/...` at the same origin -- no separate
wiring needed. Without the worker running, jobs stay `pending` forever (this is expected: M3-M5 ran
jobs synchronously in-process via `InMemoryJobRunner`; M6 made execution genuinely async).

**Windows note**: `rq.Worker` forks a subprocess per job (`os.fork()`), which doesn't exist on Windows,
and its default timeout enforcement uses `SIGALRM`, which also doesn't exist on Windows. `worker.py`
works around both: on `sys.platform == "win32"` it uses `rq.SimpleWorker` (runs jobs in-process, no
fork) with `death_penalty_class` overridden to `rq.timeouts.TimerDeathPenalty` (thread+ctypes-based,
no signals). Real `rq.Worker` is used unmodified on non-Windows platforms.

## Architecture (server/)

Strict layering under `server/src/deadair/`, dependencies point inward only (presentation →
application → domain; infrastructure implements application's ports):

- **`domain/`** — pure logic, no I/O, no framework imports.
  - `entities/` — `Job`, `Video`, `Transcript`, `EDL`. `Job` is an immutable, frozen dataclass with
    transition methods (`with_step_updated`, `cancel`) that derive overall `JobStatus` from per-step
    `StepStatus`es and raise `InvalidJobTransitionError` once a job is terminal (`DONE`/`FAILED`/`CANCELLED`).
  - `pipeline/` — the step DAG. `step.py` defines `PipelineStep` (enum) and `STEP_DEPENDENCIES`; the enum's
    *declaration order* is asserted (by `tests/unit/domain/test_step_graph.py`) to be a valid topological
    sort of the dependency graph — keep it that way when adding/reordering steps. `config_hash.py` computes
    a content hash per step from its own config + upstream hashes (recursively capturing the whole
    upstream chain), used as the cache key alongside `ArtifactKey(video_id, step, config_hash)`. Bump
    `STEP_ALGO_VERSION` in `config_hash.py` when a step's internal algorithm changes in a way that isn't
    captured by config fields, to force cache invalidation.
  - `policies/` — pure functions like `filler_policy.find_filler_words` / `silence_policy.filter_cuttable_silences`.
  - `edl_builder.py` — combines silence + filler cut ranges into an `EDL`.
- **`application/`**
  - `ports/` — abstract interfaces (`ABC`s) that infrastructure implements: `JobRepository`,
    `VideoRepository`, `ArtifactRepository`, `ProgressReporter`, `AudioExtractor`, `Transcriber`,
    `SilenceDetector`, `VideoRenderer`, `JobRunner`. Each raises its own domain-specific errors (e.g.
    `JobNotFoundError`, `JobAlreadyExistsError`) rather than leaking storage-specific exceptions.
  - `use_cases/run_pipeline_job.py` — the pipeline orchestrator. `run_pipeline_job(job_id: str)` is a
    **top-level, dotted-path-importable** function: it must never be wrapped in a closure or bound method
    before being handed to `JobRunner.enqueue`, because the real (future) RQ-based runner executes it in a
    separate worker process that imports it by dotted path and calls it with plain picklable args. It
    rebuilds its own `Container` inside the worker rather than receiving one. For each step, in DAG order,
    it computes the config hash, checks `ArtifactRepository` for a cached result (`SKIPPED_CACHED`), and
    otherwise calls the matching port method, serializes the result, and stores it before moving to the
    next step. Step failures caught from `_PORT_ERRORS` mark the step `FAILED` and stop the job; steps not
    yet implemented in `_STEP_CONFIGS` (e.g. `CHAPTERS`, `SUBTITLES`) are skipped as out-of-scope for v1.
- **`infrastructure/`** — concrete adapters for the ports above.
  - `persistence/in_memory/` — dict-backed repos, used in tests.
  - `persistence/sqlite/` — real `JobRepository`/`VideoRepository` backed by sqlite (schema in
    `persistence/sqlite/schema.sql`), used by `build_container()`.
  - `persistence/local_disk/` — `DiskArtifactRepository`, stores step artifacts as files under `data_dir/artifacts`.
  - `persistence/sqlite/progress_reporter_sqlite.py` — real `ProgressReporter`, backed by the `progress`
    table (upsert via `ON CONFLICT`). Chosen over Redis pub/sub because the API process and the RQ worker
    process already share the same sqlite db for jobs/videos -- polling reads from the same file rather
    than adding a second cross-process channel.
  - `media/fake_*.py` (`fake_audio_extractor`, `fake_transcriber`, `fake_silence_detector`,
    `fake_video_renderer`) — kept for fast/isolated orchestrator + API tests; `build_container()` no
    longer wires any of them.
  - `media/ffmpeg_runner.py` — shared subprocess helper (`run_ffmpeg`), raises `FfmpegInvocationError` with
    the last ~20 lines of stderr on a non-zero exit.
  - `media/ffmpeg_audio_extractor.py` — real `AudioExtractor`, shells out to ffmpeg to extract a mono/resampled WAV.
  - `media/ffmpeg_silence_detector.py` — real `SilenceDetector`, runs ffmpeg's `silencedetect` filter and
    regex-parses `silence_start`/`silence_end` pairs from stderr into raw candidate `TimeRange` gaps (does
    NOT apply `min_silence_duration` itself — that's `silence_policy.filter_cuttable_silences`'s job,
    called by the orchestrator).
  - `media/faster_whisper_transcriber.py` — real `Transcriber`. Lazily loads and caches a `WhisperModel`
    per adapter instance (reloads only if a job requests a different `model_name`), keyed by
    `TranscribeConfig.model_name` (per-job) while `device`/`compute_type` come from `Settings`
    (deployment-level hardware config, not per-job). Reports fractional progress via `on_progress` as each
    Whisper segment completes (`seg.end / info.duration`). Wraps any failure in `TranscriptionError`.
  - `media/ffmpeg_video_renderer.py` — real `VideoRenderer`. Re-encodes each `edl.keep_ranges` entry as its
    own segment (input-side `-ss`/`-to`, frame-accurate even under re-encode, avoiding the keyframe-
    snapping that `-c copy` segment cuts would cause), then concatenates via ffmpeg's concat demuxer
    (`-c copy`, safe since every segment shares the same just-applied codec/CRF). Single-keep-range EDLs
    skip the concat step entirely. Raises `RenderError` if `edl.keep_ranges` is empty.
  - `jobs/in_memory_job_runner.py` — synchronous, in-process `JobRunner` fake, used by tests only now.
  - `jobs/rq_job_runner.py` — real `JobRunner`. Takes an already-constructed Redis connection (not a URL),
    so it's trivially testable against `fakeredis` without a real Redis server. Sets `job_timeout` to a
    generous default (1 hour) on every enqueue, since RQ's own default (180s) is too short for a full
    extract+transcribe+render pipeline.
  - `progress/in_memory_progress_reporter.py` — in-memory `ProgressReporter` fake, used by tests only now.
- **`presentation/`** — FastAPI layer.
  - `api/app.py` — `create_app(container)` builds the `FastAPI` app, stashes the `Container` on
    `app.state.container`, mounts `videos` and `jobs` routers, registers error handlers.
  - `api/deps.py` — `get_container(request)` FastAPI dependency pulls the container back off app state.
  - `api/videos.py` — `POST /api/videos` (upload, hashes the file, probes metadata, creates a `Video` +
    `Job` with the MVP step subset `MVP_STEPS`, enqueues `run_pipeline_job`), `GET /api/videos`,
    `GET /api/videos/{id}`, `GET /api/videos/{id}/result` (streams the rendered file; 409 if render step
    isn't `DONE` yet).
  - `api/jobs.py` — `GET /api/jobs/{id}` (job + per-step progress via DTO mapper), `POST
    /api/jobs/{id}/cancel`.
  - `dto/` + `mappers/` — Pydantic response models and pure functions mapping domain entities → DTOs
    (mappers pull live progress from `ProgressReporter` where relevant).
  - `main.py` — the ASGI entrypoint: `app = create_app(build_container())`.
- **`container.py`** — the composition root. `build_container(settings=None)` is the *only* place adapters
  get wired to ports; swapping an adapter (e.g. fake → real transcriber) means changing this function, not
  call sites. `run_pipeline_job` calls `build_container()` again with no args inside the worker, so it must
  reconstruct an equivalent container from environment/settings alone — it cannot receive one by reference.
- **`config.py`** — `Settings` (pydantic-settings), env-prefixed `DEADAIR_` (e.g.
  `DEADAIR_FFMPEG_BINARY_PATH`, `DEADAIR_DATA_DIR`, `DEADAIR_REDIS_URL`, `DEADAIR_RQ_QUEUE_NAME`), loaded
  from env or `.env`, `extra="forbid"`.
- **`worker.py`** — `python -m deadair.worker` entrypoint; see the Windows note under Commands above.

## Testing conventions

- `tests/unit/` mirrors `src/deadair/` layout (`domain/`, `application/`, `presentation/`).
- `tests/contract/` holds **shared behavioral contracts** as plain classes (not directly collected by
  pytest — no `Test` prefix), e.g. `JobRepositoryContractTests` in `job_repository_contract.py`. Each
  concrete adapter (in-memory, sqlite) has a `test_*.py` in `tests/infrastructure/` that subclasses the
  contract and provides a `repo`/equivalent fixture, so the same behavior is asserted identically across
  all adapters implementing a given port. When adding a new adapter for an existing port, subclass its
  contract rather than writing fresh assertions from scratch.
- Property-based tests use `hypothesis` (e.g. `test_edl_builder_properties.py`).
- The `slow` pytest marker (declared in `server/pyproject.toml`, deselected by default via `addopts`) is
  for tests requiring real binaries/models: `tests/infrastructure/media/test_ffmpeg_audio_extractor.py`,
  `test_ffmpeg_silence_detector.py`, and `test_ffmpeg_video_renderer.py` run against a tiny committed
  fixture clip (`tests/fixtures/tone_silence_tone.mp4`, 1s tone / 1s silence / 1s tone, generated with
  ffmpeg lavfi sources); their `ffmpeg_binary_path`/`ffprobe_binary_path` fixtures resolve via
  `shutil.which` and call `pytest.skip` if missing. `test_faster_whisper_transcriber.py` runs the real
  `tiny` Whisper model against `tests/fixtures/speech_sample.wav` (real synthesized speech via Windows
  `System.Speech` TTS — Whisper needs actual speech to produce meaningful output).
- `tests/infrastructure/jobs/test_rq_job_runner.py` is NOT marked `slow` — it runs against `fakeredis`
  (an in-memory Redis simulation good enough for RQ's queue/job bookkeeping), so it needs no real Redis
  server and stays in the fast/default suite. The enqueued function must be a real importable module-level
  function (RQ rejects anything from `__main__`), which is naturally true for a function defined in a
  pytest test module.
- `tests/infrastructure/test_progress_reporter_sqlite.py` subclasses the same `ProgressReporterContractTests`
  as the in-memory adapter's test, per the contract-test convention above.
- `tests/unit/presentation/conftest.py`'s `container` fixture builds an explicit all-fake `Container` (in-
  memory repos, `InMemoryJobRunner`, fake media adapters) and `monkeypatch.setattr`s
  `deadair.application.use_cases.run_pipeline_job.build_container` to return that same instance. This is
  necessary because `run_pipeline_job` always calls `build_container()` itself with no arguments (the real
  RQ contract — see above); without the patch it would rebuild a *different* container from real
  `Settings`/env, invoking the real ffmpeg adapters against a nonexistent binary path instead of reusing
  the test's fakes.
