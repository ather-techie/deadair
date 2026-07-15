# deadair

Automated video-editing pipeline: upload a video, extract audio, transcribe it, detect
silence and filler words, build an EDL, and render the cut.

## Layout

- `server/` — Python (FastAPI) backend, built as a hexagonal / ports-and-adapters
  architecture. See `server/pyproject.toml` and `CLAUDE.md` for the architecture map.
- `client/` — static HTML/JS upload page (no build step), served directly by the FastAPI app
  at `/`. Uploads a video, polls job progress, and plays back the rendered result once done.
- `docker-compose.yml` — Redis, used as the RQ job queue's broker.

## Running it

1. Start Redis (or run a native `redis-server` on the same port instead of Docker):

   ```
   docker compose up -d redis
   ```

2. Create and activate a Python virtual environment, then install the backend and set
   the required env vars (an absolute path to an installed `ffmpeg` binary is required;
   `ffprobe` is expected alongside it) via a `server/.env` file:

   ```
   cd server
   python -m venv .venv
   source .venv/bin/activate       # macOS/Linux
   .venv\Scripts\Activate.ps1      # Windows PowerShell
   pip install -e ".[dev]"
   ```

   (On a fresh Windows machine, `Activate.ps1` may fail with "running scripts is disabled on
   this system" — run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once to allow it.)

   Then create `server/.env` with at least:

   ```
   DEADAIR_FFMPEG_BINARY_PATH=/path/to/ffmpeg
   ```

   Activate the same virtual environment in every new terminal you open for this
   project (API, worker, tests) before running the commands below.

3. Run the API:

   ```
   uvicorn deadair.presentation.main:app --reload
   ```

4. In a separate terminal, activate the same virtual environment (`.env` is picked up
   automatically from `server/`), then run the worker that actually executes the
   pipeline for each uploaded video:

   ```
   cd server
   source .venv/bin/activate       # macOS/Linux
   .venv\Scripts\Activate.ps1      # Windows PowerShell
   python -m deadair.worker
   ```

5. Open `http://localhost:8000/` in a browser — the FastAPI app serves the client directly, so
   no separate client process is needed. Upload a video and watch it progress through
   extraction, transcription, silence/filler detection, EDL building, and rendering.

## Tests

```
cd server
pytest -q              # fast suite (default; skips tests needing real ffmpeg/whisper/redis)
pytest -m slow -q      # tests against real ffmpeg, faster-whisper, and fixture media
```
