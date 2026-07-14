# deadair

Automated video-editing pipeline: upload a video, extract audio, transcribe it, detect
silence and filler words, build an EDL, and render the cut.

## Layout

- `server/` — Python (FastAPI) backend, built as a hexagonal / ports-and-adapters
  architecture. See `server/pyproject.toml` and `CLAUDE.md` for the architecture map.
- `client/` — static HTML/JS upload page (no build step). Uploads a video, polls job
  progress, and plays back the rendered result once done.
- `docker-compose.yml` — Redis, used as the RQ job queue's broker.

## Running it

1. Start Redis:

   ```
   docker compose up -d redis
   ```

2. Install the backend and set the required env vars (an absolute path to an installed
   `ffmpeg` binary is required; `ffprobe` is expected alongside it):

   ```
   cd server
   pip install -e ".[dev]"
   export DEADAIR_FFMPEG_BINARY_PATH=/path/to/ffmpeg
   ```

3. Run the API:

   ```
   uvicorn deadair.presentation.main:app --reload
   ```

4. In a separate terminal (same env vars), run the worker that actually executes the
   pipeline for each uploaded video:

   ```
   cd server
   python -m deadair.worker
   ```

5. Serve the client:

   ```
   cd client
   python -m http.server
   ```

   Open it in a browser, upload a video, and watch it progress through extraction,
   transcription, silence/filler detection, EDL building, and rendering.

## Tests

```
cd server
pytest -q              # fast suite (default; skips tests needing real ffmpeg/whisper/redis)
pytest -m slow -q      # tests against real ffmpeg, faster-whisper, and fixture media
```
