import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def create_connection(db_path: str | Path) -> sqlite3.Connection:
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI dispatches sync path operations (and
    # the TestClient's ASGI portal) onto worker threads other than the one
    # that built the Container/opened this connection.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_PATH.read_text())
    for ddl in (
        "ALTER TABLE jobs ADD COLUMN speed_multiplier REAL",
        "ALTER TABLE jobs ADD COLUMN noise_floor_db REAL",
        "ALTER TABLE jobs ADD COLUMN min_silence_duration REAL",
        "ALTER TABLE jobs ADD COLUMN padding_seconds REAL",
        "ALTER TABLE jobs ADD COLUMN min_keep_duration REAL",
        "ALTER TABLE jobs ADD COLUMN filler_words_json TEXT",
        "ALTER TABLE jobs ADD COLUMN filler_case_sensitive INTEGER",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass  # column already exists on a pre-existing on-disk db
    conn.commit()
    return conn
