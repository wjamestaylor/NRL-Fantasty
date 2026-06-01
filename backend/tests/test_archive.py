"""Tests for the historical snapshot archive module."""

from __future__ import annotations

import gzip
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app import archive


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_players(n: int = 2) -> list[dict]:
    return [
        {
            "id": f"P{i}",
            "name": f"Player {i}",
            "team": "Rabbitohs",
            "positions": ["MID"],
            "price": 700000 + i * 10000,
            "season_average": 55.0,
            "last_3_average": 54.0,
            "minutes_adjusted_base": 55.0,
            "opponent_modifier": 1,
            "role_change_modifier": 0,
            "role_risk": 0.1,
            "injury_risk": 0.1,
            "job_security_risk": 0.02,
        }
        for i in range(1, n + 1)
    ]


def _read_gz(path: Path) -> object:
    with gzip.open(path, "rb") as gz:
        return json.loads(gz.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# archive_snapshot
# ---------------------------------------------------------------------------

def test_archive_snapshot_creates_gzip_file(tmp_path: Path) -> None:
    payload = _make_players(2)
    dest = archive.archive_snapshot(tmp_path, "players", payload, date(2024, 3, 15))

    assert dest == tmp_path / "archive" / "players" / "2024-03-15.json.gz"
    assert dest.exists()
    assert _read_gz(dest) == payload


def test_archive_snapshot_uses_today_when_no_date_given(tmp_path: Path) -> None:
    payload = _make_players(1)
    dest = archive.archive_snapshot(tmp_path, "players", payload)

    today = date.today().isoformat()
    assert dest.name == f"{today}.json.gz"
    assert dest.exists()


def test_archive_snapshot_overwrites_same_day(tmp_path: Path) -> None:
    payload_v1 = _make_players(1)
    payload_v2 = _make_players(3)
    d = date(2024, 6, 1)

    archive.archive_snapshot(tmp_path, "players", payload_v1, d)
    archive.archive_snapshot(tmp_path, "players", payload_v2, d)

    dest = tmp_path / "archive" / "players" / "2024-06-01.json.gz"
    assert _read_gz(dest) == payload_v2


def test_archive_snapshot_respects_custom_archive_dir(tmp_path: Path, monkeypatch) -> None:
    custom_dir = tmp_path / "custom_archive"
    monkeypatch.setenv(archive.ARCHIVE_DIR_ENV, str(custom_dir))

    dest = archive.archive_snapshot(tmp_path, "fixtures", [{"round": 1}], date(2024, 1, 1))

    assert dest.parent.parent == custom_dir
    assert dest.exists()


# ---------------------------------------------------------------------------
# list_archived_dates
# ---------------------------------------------------------------------------

def test_list_archived_dates_returns_sorted_dates(tmp_path: Path) -> None:
    for d in [date(2024, 3, 10), date(2024, 3, 12), date(2024, 3, 11)]:
        archive.archive_snapshot(tmp_path, "players", [], d)

    dates = archive.list_archived_dates(tmp_path, "players")
    assert dates == ["2024-03-10", "2024-03-11", "2024-03-12"]


def test_list_archived_dates_empty_when_no_archive(tmp_path: Path) -> None:
    assert archive.list_archived_dates(tmp_path, "players") == []


# ---------------------------------------------------------------------------
# load_archived_snapshot
# ---------------------------------------------------------------------------

def test_load_archived_snapshot_returns_payload(tmp_path: Path) -> None:
    payload = _make_players(2)
    archive.archive_snapshot(tmp_path, "players", payload, date(2024, 5, 20))

    loaded = archive.load_archived_snapshot(tmp_path, "players", "2024-05-20")
    assert loaded == payload


def test_load_archived_snapshot_raises_for_missing_date(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        archive.load_archived_snapshot(tmp_path, "players", "2024-01-01")


def test_load_archived_snapshot_raises_for_bad_date_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid date format"):
        archive.load_archived_snapshot(tmp_path, "players", "not-a-date")


# ---------------------------------------------------------------------------
# prune_archive
# ---------------------------------------------------------------------------

def test_prune_archive_removes_old_files(tmp_path: Path) -> None:
    today = date.today()
    old_date = today - timedelta(days=40)
    recent_date = today - timedelta(days=5)

    archive.archive_snapshot(tmp_path, "players", [], old_date)
    archive.archive_snapshot(tmp_path, "players", [], recent_date)

    removed = archive.prune_archive(tmp_path, "players", keep_days=30)

    assert len(removed) == 1
    assert removed[0].name == f"{old_date.isoformat()}.json.gz"
    remaining = archive.list_archived_dates(tmp_path, "players")
    assert remaining == [recent_date.isoformat()]


def test_prune_archive_no_op_when_nothing_old(tmp_path: Path) -> None:
    today = date.today()
    archive.archive_snapshot(tmp_path, "players", [], today)

    removed = archive.prune_archive(tmp_path, "players", keep_days=30)
    assert removed == []


def test_prune_archive_raises_for_invalid_keep_days(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        archive.prune_archive(tmp_path, "players", keep_days=0)


def test_prune_archive_no_op_when_no_archive_dir(tmp_path: Path) -> None:
    assert archive.prune_archive(tmp_path, "players", keep_days=30) == []


# ---------------------------------------------------------------------------
# purge_player_from_archives
# ---------------------------------------------------------------------------

def test_purge_player_from_archives_removes_player(tmp_path: Path) -> None:
    players = _make_players(3)
    archive.archive_snapshot(tmp_path, "players", players, date(2024, 4, 1))
    archive.archive_snapshot(tmp_path, "players", players, date(2024, 4, 2))

    modified = archive.purge_player_from_archives(tmp_path, "P2")

    assert len(modified) == 2
    for d in ["2024-04-01", "2024-04-02"]:
        loaded = archive.load_archived_snapshot(tmp_path, "players", d)
        ids = [r["id"] for r in loaded]
        assert "P2" not in ids
        assert "P1" in ids
        assert "P3" in ids


def test_purge_player_not_present_returns_empty(tmp_path: Path) -> None:
    players = _make_players(2)
    archive.archive_snapshot(tmp_path, "players", players, date(2024, 4, 1))

    modified = archive.purge_player_from_archives(tmp_path, "P99")
    assert modified == []


def test_purge_player_no_op_when_no_archive_dir(tmp_path: Path) -> None:
    assert archive.purge_player_from_archives(tmp_path, "P1") == []


def test_archive_snapshot_raises_for_unknown_dataset(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown dataset"):
        archive.archive_snapshot(tmp_path, "unknown", [], date(2024, 1, 1))


def test_load_archived_snapshot_raises_for_unknown_dataset(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown dataset"):
        archive.load_archived_snapshot(tmp_path, "unknown", "2024-01-01")


def test_list_archived_dates_raises_for_unknown_dataset(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown dataset"):
        archive.list_archived_dates(tmp_path, "unknown")
