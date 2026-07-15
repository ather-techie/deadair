CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    steps_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_video_id ON jobs(video_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    fps REAL,
    width INTEGER,
    height INTEGER
);
CREATE INDEX IF NOT EXISTS idx_videos_content_hash ON videos(content_hash);

CREATE TABLE IF NOT EXISTS progress (
    job_id TEXT NOT NULL,
    step TEXT NOT NULL,
    fraction_complete REAL NOT NULL,
    message TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (job_id, step)
);

CREATE TABLE IF NOT EXISTS transcript_segments (
    job_id TEXT NOT NULL,
    seg_index INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    words_json TEXT NOT NULL,
    PRIMARY KEY (job_id, seg_index)
);
