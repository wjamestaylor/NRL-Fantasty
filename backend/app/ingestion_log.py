from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

INGESTION_LOG_PATH_ENV = "NRL_INGESTION_LOG_PATH"
DEFAULT_INGESTION_LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "ingestion_log.jsonl"


def _log_path() -> Path:
    raw = os.getenv(INGESTION_LOG_PATH_ENV)
    if raw:
        return Path(raw)
    return DEFAULT_INGESTION_LOG_PATH


def append_ingestion_event(
    source: str,
    status: str,
    record_count: int,
    error: str | None = None,
) -> None:
    """Append a single ingestion event to the audit log (JSONL file)."""
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "source": source,
        "status": status,
        "record_count": record_count,
    }
    if error is not None:
        entry["error"] = error

    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        _logger.warning("Could not write ingestion log entry for %s: %s", source, exc)


def read_ingestion_log(max_entries: int = 100) -> list[dict[str, Any]]:
    """Return the most recent ingestion log entries (up to *max_entries*)."""
    path = _log_path()
    if not path.exists():
        return []
    try:
        entries: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-max_entries:]
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Could not read ingestion log: %s", exc)
        return []
