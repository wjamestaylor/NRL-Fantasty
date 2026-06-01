import json
from pathlib import Path

from app import feed_ingestion


def _write_snapshot(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_feed_bundle_uses_snapshots_when_live_not_configured(tmp_path: Path, monkeypatch) -> None:
    players_path = tmp_path / "players.json"
    fixtures_path = tmp_path / "fixtures.json"
    news_path = tmp_path / "news.json"

    _write_snapshot(
        players_path,
        [
            {
                "id": "P1",
                "name": "Cameron Murray",
                "team": "Rabbitohs",
                "positions": ["MID"],
                "price": 760000,
                "season_average": 60,
                "last_3_average": 62,
                "minutes_adjusted_base": 61,
                "opponent_modifier": 2,
                "role_change_modifier": 0,
                "role_risk": 0.1,
                "injury_risk": 0.1,
                "job_security_risk": 0.02,
                "bye_rounds": [13],
            }
        ],
    )
    _write_snapshot(fixtures_path, [{"round": 1, "home_team": "Broncos", "away_team": "Roosters"}])
    _write_snapshot(news_path, [{"player_id": "P1", "signal": "fit", "confidence": "high"}])

    monkeypatch.setenv(feed_ingestion.PLAYERS_SNAPSHOT_PATH_ENV, str(players_path))
    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))

    bundle = feed_ingestion.load_feed_bundle()

    assert bundle.players[0].name == "Cameron Murray"
    assert bundle.fixtures[0].home_team == "Broncos"
    assert bundle.news_signals[0].signal == "fit"
    assert bundle.source_health["players"]["status"] == "snapshot"
    assert bundle.source_health["players"]["breakeven_status"] == "disabled"
    assert bundle.source_health["players"]["breakeven_reason"] == "feed_missing"


def test_load_feed_bundle_falls_back_to_snapshot_when_live_fetch_fails(
    tmp_path: Path, monkeypatch
) -> None:
    players_path = tmp_path / "players.json"
    fixtures_path = tmp_path / "fixtures.json"
    news_path = tmp_path / "news.json"

    _write_snapshot(
        players_path,
        [
            {
                "id": "P1",
                "name": "Cameron Murray",
                "team": "Rabbitohs",
                "positions": ["MID"],
                "price": 760000,
                "season_average": 60,
                "last_3_average": 62,
                "minutes_adjusted_base": 61,
                "opponent_modifier": 2,
                "role_change_modifier": 0,
                "role_risk": 0.1,
                "injury_risk": 0.1,
                "job_security_risk": 0.02,
                "bye_rounds": [13],
            }
        ],
    )
    _write_snapshot(fixtures_path, [{"round": 1, "home_team": "Broncos", "away_team": "Roosters"}])
    _write_snapshot(news_path, [{"player_id": "P1", "signal": "fit", "confidence": "high"}])

    monkeypatch.setenv(feed_ingestion.PLAYERS_SNAPSHOT_PATH_ENV, str(players_path))
    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))
    monkeypatch.setenv(feed_ingestion.PLAYERS_FEED_URL_ENV, "https://invalid/players")
    monkeypatch.setenv(feed_ingestion.FIXTURES_FEED_URL_ENV, "https://invalid/fixtures")
    monkeypatch.setenv(feed_ingestion.NEWS_FEED_URL_ENV, "https://invalid/news")

    def fake_fetch_json(url: str, retries: int = 3) -> list[dict]:
        raise RuntimeError(f"unavailable: {url}")

    monkeypatch.setattr(feed_ingestion, "_fetch_json", fake_fetch_json)

    bundle = feed_ingestion.load_feed_bundle()

    assert bundle.source_health["players"]["status"] == "snapshot_fallback"
    assert bundle.source_health["players"]["breakeven_status"] == "disabled"
    assert bundle.source_health["fixtures"]["status"] == "snapshot_fallback"
    assert bundle.source_health["news"]["status"] == "snapshot_fallback"


def test_refresh_snapshots_from_live_feeds_writes_validated_snapshots(
    tmp_path: Path, monkeypatch
) -> None:
    players_path = tmp_path / "players.json"
    fixtures_path = tmp_path / "fixtures.json"
    news_path = tmp_path / "news.json"

    monkeypatch.setenv(feed_ingestion.PLAYERS_SNAPSHOT_PATH_ENV, str(players_path))
    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))
    monkeypatch.setenv(feed_ingestion.PLAYERS_FEED_URL_ENV, "https://live/players")
    monkeypatch.setenv(feed_ingestion.FIXTURES_FEED_URL_ENV, "https://live/fixtures")
    monkeypatch.setenv(feed_ingestion.NEWS_FEED_URL_ENV, "https://live/news")

    def fake_fetch_json(url: str, _retries: int = 3) -> list[dict]:
        if url.endswith("players"):
            return [
                {
                    "id": "P1",
                    "name": "Cameron Murray",
                    "team": "Rabbitohs",
                    "positions": ["MID"],
                    "price": 760000,
                    "season_average": 60,
                    "last_3_average": 62,
                    "minutes_adjusted_base": 61,
                    "opponent_modifier": 2,
                    "role_change_modifier": 0,
                    "role_risk": 0.1,
                    "injury_risk": 0.1,
                    "job_security_risk": 0.02,
                    "bye_rounds": [13],
                }
            ]
        if url.endswith("fixtures"):
            return [{"round": 1, "home_team": "Broncos", "away_team": "Roosters"}]
        return [{"player_id": "P1", "signal": "fit", "confidence": "high"}]

    monkeypatch.setattr(feed_ingestion, "_fetch_json", fake_fetch_json)

    bundle = feed_ingestion.refresh_snapshots_from_live_feeds()

    assert players_path.exists()
    assert fixtures_path.exists()
    assert news_path.exists()
    assert bundle.source_health["players"]["status"] == "live"
    assert bundle.source_health["players"]["breakeven_status"] == "disabled"
    assert bundle.source_health["fixtures"]["status"] == "live"
    assert bundle.source_health["news"]["status"] == "live"


def test_load_feed_bundle_disables_breakeven_when_feed_is_incomplete(
    tmp_path: Path, monkeypatch
) -> None:
    players_path = tmp_path / "players.json"
    fixtures_path = tmp_path / "fixtures.json"
    news_path = tmp_path / "news.json"

    _write_snapshot(
        players_path,
        [
            {
                "id": "P1",
                "name": "Cameron Murray",
                "team": "Rabbitohs",
                "positions": ["MID"],
                "price": 760000,
                "season_average": 60,
                "last_3_average": 62,
                "minutes_adjusted_base": 61,
                "opponent_modifier": 2,
                "role_change_modifier": 0,
                "role_risk": 0.1,
                "injury_risk": 0.1,
                "job_security_risk": 0.02,
                "breakeven": 58,
                "bye_rounds": [13],
            },
            {
                "id": "P2",
                "name": "Reed Mahoney",
                "team": "Bulldogs",
                "positions": ["HOK"],
                "price": 690000,
                "season_average": 54,
                "last_3_average": 52,
                "minutes_adjusted_base": 53,
                "opponent_modifier": 1,
                "role_change_modifier": 0,
                "role_risk": 0.1,
                "injury_risk": 0.1,
                "job_security_risk": 0.02,
                "bye_rounds": [13],
            },
        ],
    )
    _write_snapshot(fixtures_path, [{"round": 1, "home_team": "Broncos", "away_team": "Roosters"}])
    _write_snapshot(news_path, [{"player_id": "P1", "signal": "fit", "confidence": "high"}])

    monkeypatch.setenv(feed_ingestion.PLAYERS_SNAPSHOT_PATH_ENV, str(players_path))
    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))

    bundle = feed_ingestion.load_feed_bundle()

    assert bundle.source_health["players"]["breakeven_status"] == "disabled"
    assert bundle.source_health["players"]["breakeven_reason"] == "incomplete_feed"
    assert all(player.breakeven is None for player in bundle.players)


def test_load_feed_bundle_enables_breakeven_when_feed_is_complete(
    tmp_path: Path, monkeypatch
) -> None:
    players_path = tmp_path / "players.json"
    fixtures_path = tmp_path / "fixtures.json"
    news_path = tmp_path / "news.json"

    _write_snapshot(
        players_path,
        [
            {
                "id": "P1",
                "name": "Cameron Murray",
                "team": "Rabbitohs",
                "positions": ["MID"],
                "price": 760000,
                "season_average": 60,
                "last_3_average": 62,
                "minutes_adjusted_base": 61,
                "opponent_modifier": 2,
                "role_change_modifier": 0,
                "role_risk": 0.1,
                "injury_risk": 0.1,
                "job_security_risk": 0.02,
                "breakeven": 58,
                "bye_rounds": [13],
            }
        ],
    )
    _write_snapshot(fixtures_path, [{"round": 1, "home_team": "Broncos", "away_team": "Roosters"}])
    _write_snapshot(news_path, [{"player_id": "P1", "signal": "fit", "confidence": "high"}])

    monkeypatch.setenv(feed_ingestion.PLAYERS_SNAPSHOT_PATH_ENV, str(players_path))
    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))

    bundle = feed_ingestion.load_feed_bundle()

    assert bundle.source_health["players"]["breakeven_status"] == "enabled"
    assert bundle.source_health["players"]["breakeven_reason"] == "complete_coverage"
    assert bundle.players[0].breakeven == 58
