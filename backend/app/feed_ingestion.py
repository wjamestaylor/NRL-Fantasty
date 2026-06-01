from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx

from . import ingestion_log as _ingestion_log
from .archive import archive_snapshot
from .models import Fixture, NewsSignal, Player

_logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_PLAYERS_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "players_snapshot.json"
DEFAULT_FIXTURES_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "fixtures_snapshot.json"
DEFAULT_NEWS_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "news_snapshot.json"
DEFAULT_PLAYER_PRICE_HISTORY_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "player_price_history_snapshot.json"
DEFAULT_PLAYER_GAME_DETAILS_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "player_game_details_snapshot.json"

PLAYERS_FEED_URL_ENV = "NRL_PLAYERS_FEED_URL"
FIXTURES_FEED_URL_ENV = "NRL_FIXTURES_FEED_URL"
NEWS_FEED_URL_ENV = "NRL_NEWS_FEED_URL"
PLAYER_PRICE_HISTORY_FEED_URL_ENV = "NRL_PLAYER_PRICE_HISTORY_FEED_URL"
PLAYER_GAME_DETAILS_FEED_URL_ENV = "NRL_PLAYER_GAME_DETAILS_FEED_URL"

PLAYERS_SNAPSHOT_PATH_ENV = "NRL_PLAYERS_SNAPSHOT_PATH"
FIXTURES_SNAPSHOT_PATH_ENV = "NRL_FIXTURES_SNAPSHOT_PATH"
NEWS_SNAPSHOT_PATH_ENV = "NRL_NEWS_SNAPSHOT_PATH"
PLAYER_PRICE_HISTORY_SNAPSHOT_PATH_ENV = "NRL_PLAYER_PRICE_HISTORY_SNAPSHOT_PATH"
PLAYER_GAME_DETAILS_SNAPSHOT_PATH_ENV = "NRL_PLAYER_GAME_DETAILS_SNAPSHOT_PATH"


@dataclass(frozen=True)
class FeedBundle:
    players: list[Player]
    fixtures: list[Fixture]
    news_signals: list[NewsSignal]
    source_health: dict[str, dict[str, Any]]
    loaded_at: str


def _snapshot_path(env_name: str, fallback: Path) -> Path:
    raw_path = os.getenv(env_name)
    if raw_path:
        return Path(raw_path)
    return fallback


def _fetch_json(url: str, retries: int = 3) -> Any:
    timeout = httpx.Timeout(10.0, connect=5.0)
    last_error: Exception | None = None
    with httpx.Client(timeout=timeout) as client:
        for _ in range(retries):
            try:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
    raise RuntimeError(f"Could not fetch feed {url}: {last_error}") from last_error


def _load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as tmp_file:
        json.dump(payload, tmp_file, indent=2)
        tmp_file.write("\n")
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)


def _validate_payload(
    payload: Any,
    model_type: type[Player] | type[Fixture] | type[NewsSignal],
) -> list[Player] | list[Fixture] | list[NewsSignal]:
    return [model_type.model_validate(item) for item in payload]


def _normalize_player_supplemental_payload(payload: Any, key: str) -> dict[str, list[dict[str, Any]]]:
    if isinstance(payload, dict):
        return {
            str(player_id): [entry for entry in records if isinstance(entry, dict)]
            for player_id, records in payload.items()
            if isinstance(records, list)
        }

    if isinstance(payload, list):
        normalized: dict[str, list[dict[str, Any]]] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            player_id = item.get("player_id")
            records = item.get(key)
            if not player_id or not isinstance(records, list):
                continue
            normalized[str(player_id)] = [entry for entry in records if isinstance(entry, dict)]
        return normalized

    return {}


def _load_optional_player_supplemental_dataset(
    name: str,
    key: str,
    feed_url: str | None,
    snapshot_path: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    now = datetime.now(UTC).isoformat()

    if feed_url:
        try:
            payload = _fetch_json(feed_url)
            records = _normalize_player_supplemental_payload(payload, key)
            count = len(records)
            health: dict[str, Any] = {
                "status": "live",
                "source": feed_url,
                "dataset": name,
                "record_count": count,
                "ingested_at": now,
            }
            _logger.info("Loaded %d records for %s from live feed %s", count, name, feed_url)
            _ingestion_log.append_ingestion_event(source=name, status="live", record_count=count)
            return records, health
        except RuntimeError as exc:
            last_error = str(exc)
            _logger.warning("Live feed failed for %s: %s — falling back to snapshot", name, exc)
            if snapshot_path.exists():
                payload = _load_json_file(snapshot_path)
                records = _normalize_player_supplemental_payload(payload, key)
                count = len(records)
                health = {
                    "status": "snapshot_fallback",
                    "source": str(snapshot_path),
                    "dataset": name,
                    "record_count": count,
                    "ingested_at": now,
                    "last_error": last_error,
                }
                _logger.info(
                    "Loaded %d records for %s from snapshot (fallback)", count, name
                )
                _ingestion_log.append_ingestion_event(
                    source=name, status="snapshot_fallback", record_count=count, error=last_error
                )
                return records, health
            health = {
                "status": "not_configured",
                "source": "none",
                "dataset": name,
                "record_count": 0,
                "ingested_at": now,
                "last_error": last_error,
            }
            _ingestion_log.append_ingestion_event(
                source=name, status="not_configured", record_count=0, error=last_error
            )
            return {}, health

    if snapshot_path.exists():
        payload = _load_json_file(snapshot_path)
        records = _normalize_player_supplemental_payload(payload, key)
        count = len(records)
        health = {
            "status": "snapshot",
            "source": str(snapshot_path),
            "dataset": name,
            "record_count": count,
            "ingested_at": now,
        }
        _logger.info("Loaded %d records for %s from snapshot", count, name)
        _ingestion_log.append_ingestion_event(source=name, status="snapshot", record_count=count)
        return records, health

    health = {
        "status": "not_configured",
        "source": "none",
        "dataset": name,
        "record_count": 0,
        "ingested_at": now,
    }
    _logger.info("Source %s is not configured (no feed URL or snapshot)", name)
    _ingestion_log.append_ingestion_event(source=name, status="not_configured", record_count=0)
    return {}, health


def _load_dataset(
    name: str,
    model_type: type[Player] | type[Fixture] | type[NewsSignal],
    feed_url: str | None,
    snapshot_path: Path,
) -> tuple[list[Player] | list[Fixture] | list[NewsSignal], dict[str, Any]]:
    now = datetime.now(UTC).isoformat()
    last_error: str | None = None

    if feed_url:
        try:
            payload = _fetch_json(feed_url)
            records = _validate_payload(payload, model_type)
            count = len(records)
            health: dict[str, Any] = {
                "status": "live",
                "source": feed_url,
                "dataset": name,
                "record_count": count,
                "ingested_at": now,
            }
            _logger.info("Loaded %d records for %s from live feed %s", count, name, feed_url)
            _ingestion_log.append_ingestion_event(source=name, status="live", record_count=count)
            return records, health
        except RuntimeError as exc:
            last_error = str(exc)
            _logger.warning("Live feed failed for %s: %s — falling back to snapshot", name, exc)

    payload = _load_json_file(snapshot_path)
    records = _validate_payload(payload, model_type)
    count = len(records)
    source_type = "snapshot_fallback" if feed_url else "snapshot"
    health = {
        "status": source_type,
        "source": str(snapshot_path),
        "dataset": name,
        "record_count": count,
        "ingested_at": now,
    }
    if last_error is not None:
        health["last_error"] = last_error
    _logger.info("Loaded %d records for %s from %s (%s)", count, name, snapshot_path, source_type)
    _ingestion_log.append_ingestion_event(
        source=name, status=source_type, record_count=count, error=last_error
    )
    return records, health


def _resolve_breakeven_support(players: list[Player]) -> tuple[list[Player], dict[str, str]]:
    total_players = len(players)
    available_breakevens = sum(player.breakeven is not None for player in players)

    if total_players > 0 and available_breakevens == total_players:
        return players, {
            "breakeven_status": "enabled",
            "breakeven_reason": "complete_coverage",
            "breakeven_coverage": f"{available_breakevens}/{total_players}",
        }

    disabled_players = [
        player if player.breakeven is None else player.model_copy(update={"breakeven": None})
        for player in players
    ]
    reason = "feed_missing" if available_breakevens == 0 else "incomplete_feed"
    return disabled_players, {
        "breakeven_status": "disabled",
        "breakeven_reason": reason,
        "breakeven_coverage": f"{available_breakevens}/{total_players}",
    }


def load_feed_bundle() -> FeedBundle:
    players_snapshot = _snapshot_path(PLAYERS_SNAPSHOT_PATH_ENV, DEFAULT_PLAYERS_SNAPSHOT_PATH)
    fixtures_snapshot = _snapshot_path(FIXTURES_SNAPSHOT_PATH_ENV, DEFAULT_FIXTURES_SNAPSHOT_PATH)
    news_snapshot = _snapshot_path(NEWS_SNAPSHOT_PATH_ENV, DEFAULT_NEWS_SNAPSHOT_PATH)
    player_price_history_snapshot = _snapshot_path(
        PLAYER_PRICE_HISTORY_SNAPSHOT_PATH_ENV,
        DEFAULT_PLAYER_PRICE_HISTORY_SNAPSHOT_PATH,
    )
    player_game_details_snapshot = _snapshot_path(
        PLAYER_GAME_DETAILS_SNAPSHOT_PATH_ENV,
        DEFAULT_PLAYER_GAME_DETAILS_SNAPSHOT_PATH,
    )

    players, players_health = _load_dataset(
        name="players",
        model_type=Player,
        feed_url=os.getenv(PLAYERS_FEED_URL_ENV),
        snapshot_path=players_snapshot,
    )
    fixtures, fixtures_health = _load_dataset(
        name="fixtures",
        model_type=Fixture,
        feed_url=os.getenv(FIXTURES_FEED_URL_ENV),
        snapshot_path=fixtures_snapshot,
    )
    news, news_health = _load_dataset(
        name="news",
        model_type=NewsSignal,
        feed_url=os.getenv(NEWS_FEED_URL_ENV),
        snapshot_path=news_snapshot,
    )
    news_health = news_health | {
        "phase5_capabilities": {
            "rich_news_fields": True,
            "categories_supported": [
                "team_list",
                "injury",
                "origin_rest",
                "role_change",
                "coach_sentiment",
                "general",
            ],
        }
    }
    price_history_by_player, price_history_health = _load_optional_player_supplemental_dataset(
        name="player_price_history",
        key="price_history",
        feed_url=os.getenv(PLAYER_PRICE_HISTORY_FEED_URL_ENV),
        snapshot_path=player_price_history_snapshot,
    )
    game_details_by_player, game_details_health = _load_optional_player_supplemental_dataset(
        name="player_game_details",
        key="game_details",
        feed_url=os.getenv(PLAYER_GAME_DETAILS_FEED_URL_ENV),
        snapshot_path=player_game_details_snapshot,
    )
    players, breakeven_health = _resolve_breakeven_support(players)

    enriched_players: list[Player] = []
    for player in players:
        updates: dict[str, Any] = {}
        if player.id in price_history_by_player:
            updates["price_history"] = price_history_by_player[player.id]
        if player.id in game_details_by_player:
            updates["game_details"] = game_details_by_player[player.id]

        if updates:
            enriched_players.append(Player.model_validate(player.model_dump() | updates))
        else:
            enriched_players.append(player)

    return FeedBundle(
        players=enriched_players,
        fixtures=fixtures,
        news_signals=news,
        source_health={
            "players": players_health | breakeven_health,
            "fixtures": fixtures_health,
            "news": news_health,
            "player_price_history": price_history_health,
            "player_game_details": game_details_health,
        },
        loaded_at=datetime.now(UTC).isoformat(),
    )


def refresh_snapshots_from_live_feeds() -> FeedBundle:
    players_url = os.getenv(PLAYERS_FEED_URL_ENV)
    fixtures_url = os.getenv(FIXTURES_FEED_URL_ENV)
    news_url = os.getenv(NEWS_FEED_URL_ENV)

    if not players_url or not fixtures_url or not news_url:
        raise RuntimeError(
            "Missing live feed configuration. Set NRL_PLAYERS_FEED_URL, NRL_FIXTURES_FEED_URL, and NRL_NEWS_FEED_URL."
        )

    players_payload = _fetch_json(players_url)
    fixtures_payload = _fetch_json(fixtures_url)
    news_payload = _fetch_json(news_url)

    validated_players = _validate_payload(players_payload, Player)
    validated_fixtures = _validate_payload(fixtures_payload, Fixture)
    validated_news = _validate_payload(news_payload, NewsSignal)

    players_snapshot_path = _snapshot_path(PLAYERS_SNAPSHOT_PATH_ENV, DEFAULT_PLAYERS_SNAPSHOT_PATH)
    fixtures_snapshot_path = _snapshot_path(FIXTURES_SNAPSHOT_PATH_ENV, DEFAULT_FIXTURES_SNAPSHOT_PATH)
    news_snapshot_path = _snapshot_path(NEWS_SNAPSHOT_PATH_ENV, DEFAULT_NEWS_SNAPSHOT_PATH)

    _write_json_file(
        players_snapshot_path,
        [player.model_dump() for player in validated_players],
    )
    _write_json_file(
        fixtures_snapshot_path,
        [fixture.model_dump() for fixture in validated_fixtures],
    )
    _write_json_file(
        news_snapshot_path,
        [signal.model_dump() for signal in validated_news],
    )

    data_dir = players_snapshot_path.parent
    archive_snapshot(data_dir, "players", [player.model_dump() for player in validated_players])
    archive_snapshot(data_dir, "fixtures", [fixture.model_dump() for fixture in validated_fixtures])
    archive_snapshot(data_dir, "news", [signal.model_dump() for signal in validated_news])

    return load_feed_bundle()


if __name__ == "__main__":
    refresh_snapshots_from_live_feeds()
