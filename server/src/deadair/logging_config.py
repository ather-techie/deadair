"""Process-wide logging setup, shared by the API and worker entrypoints.

Writes to a dated file under Settings.log_dir (e.g. log/deadair-2026-07-14.log)
in addition to stderr, so logs from both the uvicorn process and the RQ worker
process land on disk without needing a separate log-shipping setup.
"""

import logging
from datetime import date

from deadair.config import Settings


def configure_logging(settings: Settings) -> None:
    log_dir = settings.resolved_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"deadair-{date.today().isoformat()}.log"

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
