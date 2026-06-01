from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx

from .models import Fixture, NewsSignal, Player

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_PLAYERS_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "players_snapshot.json"
DEFAULT_FIXTURES_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "fixtures_snapshot.json"
DEFAULT_NEWS_SNAPSHOT_PATH = DEFAULT_DATA_DIR / "news_snapshot.json"

PLAYERS_FEED_URL_ENV = "NRL_PLAYERS_FEED_URL"
FIXTURES_FEED_URL_ENV = "NRL_FIXTURES_FEED_URL"
NEWS_FEED_URL_ENV = "NRL_NEWS_FEED_URL"

PLAYERS_SNAPSHOT_PATH_ENV = "NRL_PLAYERS_SNAPSHOT_PATH"
FIXTURES_SNAPSHOT_PATH_ENV = "NRL_FIXTURES_SNAPSHOT_PATH"
NEWS_SNAPSHOT_PATH_ENV = "NRL_NEWS_SNAPSHOT_PATH"


@dataclass(frozen=True)
class FeedBundle:
    players: list[Player]
    fixtures: list[Fixture]
    news_signals: list[NewsSignal]
    source_health: dict[str, dict[str, str]]
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


def _load_dataset(
    name: str,
    model_type: type[Player] | type[Fixture] | type[NewsSignal],
    feed_url: str | None,
    snapshot_path: Path,
) -> tuple[list[Player] | list[Fixture] | list[NewsSignal], dict[str, str]]:
    if feed_url:
        try:
            payload = _fetch_json(feed_url)
            records = _validate_payload(payload, model_type)
            return records, {"status": "live", "source": feed_url, "dataset": name}
        except RuntimeError:
            pass

    payload = _load_json_file(snapshot_path)
    records = _validate_payload(payload, model_type)
    source_type = "snapshot_fallback" if feed_url else "snapshot"
    return records, {"status": source_type, "source": str(snapshot_path), "dataset": name}


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
    players, breakeven_health = _resolve_breakeven_support(players)

    return FeedBundle(
        players=players,
        fixtures=fixtures,
        news_signals=news,
        source_health={
            "players": players_health | breakeven_health,
            "fixtures": fixtures_health,
            "news": news_health,
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

    _write_json_file(
        _snapshot_path(PLAYERS_SNAPSHOT_PATH_ENV, DEFAULT_PLAYERS_SNAPSHOT_PATH),
        [player.model_dump() for player in validated_players],
    )
    _write_json_file(
        _snapshot_path(FIXTURES_SNAPSHOT_PATH_ENV, DEFAULT_FIXTURES_SNAPSHOT_PATH),
        [fixture.model_dump() for fixture in validated_fixtures],
    )
    _write_json_file(
        _snapshot_path(NEWS_SNAPSHOT_PATH_ENV, DEFAULT_NEWS_SNAPSHOT_PATH),
        [signal.model_dump() for signal in validated_news],
    )

    return load_feed_bundle()


if __name__ == "__main__":
    refresh_snapshots_from_live_feeds()
