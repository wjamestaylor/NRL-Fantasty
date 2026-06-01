"""Historical snapshot archiving for player and fixture data.

Snapshots are written as gzip-compressed JSON files under
``<data_dir>/archive/<dataset>/<YYYY-MM-DD>.json.gz``.  One file per
dataset per calendar date is retained; a second run on the same day
overwrites the earlier file so the archive always reflects the latest
intra-day refresh.

Retrieval
---------
``list_archived_dates(data_dir, dataset)``   -> sorted list of ISO date strings
``load_archived_snapshot(data_dir, dataset, date)`` -> raw list/dict payload

Retention / backup hygiene
--------------------------
``prune_archive(data_dir, dataset, keep_days)`` removes entries older than
*keep_days* to bound storage growth.

GDPR compliance
---------------
``purge_player_from_archives(data_dir, player_id)`` rewrites every archived
players snapshot, stripping all records whose ``id`` field matches the
supplied *player_id*.  This satisfies a right-to-erasure request without
destroying the remaining historical data.
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

DEFAULT_ARCHIVE_SUBDIR = "archive"
ARCHIVE_DIR_ENV = "NRL_ARCHIVE_DIR"


def _archive_dir(data_dir: Path) -> Path:
    raw = os.getenv(ARCHIVE_DIR_ENV)
    if raw:
        return Path(raw)
    return data_dir / DEFAULT_ARCHIVE_SUBDIR


def _dataset_dir(data_dir: Path, dataset: str) -> Path:
    return _archive_dir(data_dir) / dataset


def _archive_path(data_dir: Path, dataset: str, snapshot_date: date) -> Path:
    return _dataset_dir(data_dir, dataset) / f"{snapshot_date.isoformat()}.json.gz"


def _write_gz(path: Path, payload: Any) -> None:
    """Atomically write *payload* as gzip-compressed JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    with NamedTemporaryFile("wb", delete=False, dir=path.parent) as tmp:
        with gzip.GzipFile(fileobj=tmp, mode="wb", mtime=0) as gz:
            gz.write(encoded)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _read_gz(path: Path) -> Any:
    """Return the decoded JSON payload from a gzip-compressed snapshot file."""
    with gzip.open(path, "rb") as gz:
        return json.loads(gz.read().decode("utf-8"))


def archive_snapshot(data_dir: Path, dataset: str, payload: Any, snapshot_date: date | None = None) -> Path:
    """Archive *payload* for *dataset* on *snapshot_date* (defaults to today UTC).

    Returns the path of the written archive file.
    """
    effective_date = snapshot_date or datetime.now(UTC).date()
    dest = _archive_path(data_dir, dataset, effective_date)
    _write_gz(dest, payload)
    return dest


def _stem(path: Path) -> str:
    """Return the filename without both .json and .gz suffixes."""
    return path.name.removesuffix(".json.gz")


def list_archived_dates(data_dir: Path, dataset: str) -> list[str]:
    """Return a sorted list of ISO date strings for which an archive exists."""
    dataset_dir = _dataset_dir(data_dir, dataset)
    if not dataset_dir.is_dir():
        return []
    dates = sorted(
        _stem(p)
        for p in dataset_dir.glob("*.json.gz")
        if _stem(p).count("-") == 2  # basic sanity check
    )
    return dates


def load_archived_snapshot(data_dir: Path, dataset: str, snapshot_date: str) -> Any:
    """Load and return the archived payload for *dataset* on *snapshot_date*.

    *snapshot_date* must be an ISO-format date string (``YYYY-MM-DD``).

    Raises ``FileNotFoundError`` if no archive exists for that date.
    """
    try:
        parsed_date = date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise ValueError(f"Invalid date format {snapshot_date!r}; expected YYYY-MM-DD") from exc

    path = _archive_path(data_dir, dataset, parsed_date)
    if not path.exists():
        raise FileNotFoundError(f"No archive for dataset={dataset!r} date={snapshot_date!r}")
    return _read_gz(path)


def prune_archive(data_dir: Path, dataset: str, keep_days: int) -> list[Path]:
    """Remove archive files older than *keep_days* days.

    Returns the list of paths that were deleted.
    """
    if keep_days < 1:
        raise ValueError("keep_days must be at least 1")

    cutoff = datetime.now(UTC).date()
    dataset_dir = _dataset_dir(data_dir, dataset)
    if not dataset_dir.is_dir():
        return []

    removed: list[Path] = []
    for path in sorted(dataset_dir.glob("*.json.gz")):
        try:
            file_date = date.fromisoformat(_stem(path))
        except ValueError:
            continue
        age = (cutoff - file_date).days
        if age > keep_days:
            path.unlink()
            removed.append(path)
    return removed


def purge_player_from_archives(data_dir: Path, player_id: str) -> list[Path]:
    """Remove all records for *player_id* from every players archive snapshot.

    Rewrites each affected file in-place.  Snapshots that already contain no
    record for the player are left untouched.  Returns the list of archive
    files that were modified.

    This operation satisfies a GDPR right-to-erasure request for a single
    player without destroying the historical record for other players.
    """
    players_dir = _dataset_dir(data_dir, "players")
    if not players_dir.is_dir():
        return []

    modified: list[Path] = []
    for path in sorted(players_dir.glob("*.json.gz")):
        try:
            payload = _read_gz(path)
        except Exception:
            continue

        if not isinstance(payload, list):
            continue

        filtered = [record for record in payload if record.get("id") != player_id]
        if len(filtered) != len(payload):
            _write_gz(path, filtered)
            modified.append(path)

    return modified
