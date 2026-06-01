import json
from pathlib import Path

from app import ingestion_log


def test_append_and_read_ingestion_event(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "test_log.jsonl"
    monkeypatch.setenv(ingestion_log.INGESTION_LOG_PATH_ENV, str(log_path))

    ingestion_log.append_ingestion_event(source="players", status="live", record_count=42)
    ingestion_log.append_ingestion_event(
        source="fixtures",
        status="snapshot_fallback",
        record_count=10,
        error="feed unreachable",
    )

    entries = ingestion_log.read_ingestion_log(max_entries=100)

    assert len(entries) == 2
    assert entries[0]["source"] == "players"
    assert entries[0]["status"] == "live"
    assert entries[0]["record_count"] == 42
    assert "error" not in entries[0]

    assert entries[1]["source"] == "fixtures"
    assert entries[1]["status"] == "snapshot_fallback"
    assert entries[1]["record_count"] == 10
    assert entries[1]["error"] == "feed unreachable"


def test_read_ingestion_log_returns_empty_when_no_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(ingestion_log.INGESTION_LOG_PATH_ENV, str(tmp_path / "missing.jsonl"))
    assert ingestion_log.read_ingestion_log() == []


def test_read_ingestion_log_respects_max_entries(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "test_log.jsonl"
    monkeypatch.setenv(ingestion_log.INGESTION_LOG_PATH_ENV, str(log_path))

    for i in range(10):
        ingestion_log.append_ingestion_event(source=f"src{i}", status="live", record_count=i)

    entries = ingestion_log.read_ingestion_log(max_entries=3)
    assert len(entries) == 3
    # Should return the LAST 3 entries
    assert entries[-1]["source"] == "src9"


def test_append_ingestion_event_writes_valid_jsonl(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "test_log.jsonl"
    monkeypatch.setenv(ingestion_log.INGESTION_LOG_PATH_ENV, str(log_path))

    ingestion_log.append_ingestion_event(source="news", status="snapshot", record_count=5)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["source"] == "news"
    assert "timestamp" in entry
