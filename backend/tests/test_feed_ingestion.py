import json
from pathlib import Path

from app import feed_ingestion
from app.models import Player, TeamGameStat


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


def test_load_feed_bundle_enriches_players_with_supplemental_snapshots(
    tmp_path: Path, monkeypatch
) -> None:
    players_path = tmp_path / "players.json"
    fixtures_path = tmp_path / "fixtures.json"
    news_path = tmp_path / "news.json"
    player_price_history_path = tmp_path / "player_price_history.json"
    player_game_details_path = tmp_path / "player_game_details.json"

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
    _write_snapshot(
        player_price_history_path,
        [{"player_id": "P1", "price_history": [{"round": 1, "price": 750000}]}],
    )
    _write_snapshot(
        player_game_details_path,
        [{"player_id": "P1", "game_details": [{"round": 1, "score": 55, "minutes": 67}]}],
    )

    monkeypatch.setenv(feed_ingestion.PLAYERS_SNAPSHOT_PATH_ENV, str(players_path))
    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))
    monkeypatch.setenv(
        feed_ingestion.PLAYER_PRICE_HISTORY_SNAPSHOT_PATH_ENV,
        str(player_price_history_path),
    )
    monkeypatch.setenv(
        feed_ingestion.PLAYER_GAME_DETAILS_SNAPSHOT_PATH_ENV,
        str(player_game_details_path),
    )

    bundle = feed_ingestion.load_feed_bundle()

    assert bundle.players[0].price_history[0].price == 750000
    assert bundle.players[0].game_details[0].minutes == 67
    assert bundle.source_health["player_price_history"]["status"] == "snapshot"
    assert bundle.source_health["player_game_details"]["status"] == "snapshot"


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


def test_load_feed_bundle_includes_record_count_and_ingested_at(
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

    bundle = feed_ingestion.load_feed_bundle()

    for source_name in ("players", "fixtures", "news"):
        health = bundle.source_health[source_name]
        assert "record_count" in health, f"{source_name} missing record_count"
        assert "ingested_at" in health, f"{source_name} missing ingested_at"
        assert isinstance(health["record_count"], int)
        assert isinstance(health["ingested_at"], str)

    assert bundle.source_health["players"]["record_count"] == 1
    assert bundle.source_health["fixtures"]["record_count"] == 1
    assert bundle.source_health["news"]["record_count"] == 1


def test_load_feed_bundle_records_last_error_on_fallback(
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

    for source_name in ("players", "fixtures", "news"):
        health = bundle.source_health[source_name]
        assert health["status"] == "snapshot_fallback"
        assert "last_error" in health, f"{source_name} missing last_error on fallback"
        assert "unavailable" in health["last_error"]


def test_load_feed_bundle_accepts_rich_news_signals_and_sets_phase5_metadata(
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
    _write_snapshot(
        news_path,
        [
            {
                "player_id": "P1",
                "signal": "hamstring concern",
                "confidence": "high",
                "category": "injury",
                "impact_score": -0.6,
                "sentiment": "negative",
                "availability_status": "doubtful",
                "round": 12,
                "source": "teamlist",
                "details": "Late fitness test",
            }
        ],
    )

    monkeypatch.setenv(feed_ingestion.PLAYERS_SNAPSHOT_PATH_ENV, str(players_path))
    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))

    bundle = feed_ingestion.load_feed_bundle()

    signal = bundle.news_signals[0]
    assert signal.category == "injury"
    assert signal.availability_status == "doubtful"
    assert signal.round == 12
    assert bundle.source_health["news"]["phase5_capabilities"]["rich_news_fields"] is True


def test_load_feed_bundle_uses_player_stats_website_when_configured(
    tmp_path: Path, monkeypatch
) -> None:
    fixtures_path = tmp_path / "fixtures.json"
    news_path = tmp_path / "news.json"

    _write_snapshot(fixtures_path, [{"round": 1, "home_team": "Broncos", "away_team": "Roosters"}])
    _write_snapshot(news_path, [{"player_id": "P1", "signal": "fit", "confidence": "high"}])

    monkeypatch.setenv(feed_ingestion.FIXTURES_SNAPSHOT_PATH_ENV, str(fixtures_path))
    monkeypatch.setenv(feed_ingestion.NEWS_SNAPSHOT_PATH_ENV, str(news_path))
    monkeypatch.setenv(feed_ingestion.PLAYER_STATS_WEBSITE_URL_ENV, "https://example.com/players")

    monkeypatch.setattr(
        feed_ingestion,
        "scrape_player_stats",
        lambda _url: [
            Player(
                id="P1",
                name="Cameron Murray",
                team="Rabbitohs",
                positions=["MID"],
                price=760000,
                season_average=60,
                last_3_average=62,
                minutes_adjusted_base=61,
                opponent_modifier=2,
                role_change_modifier=0,
                role_risk=0.1,
                injury_risk=0.1,
                job_security_risk=0.02,
                bye_rounds=[13],
            )
        ],
    )

    bundle = feed_ingestion.load_feed_bundle()

    assert bundle.players[0].id == "P1"
    assert bundle.source_health["players"]["status"] == "website"


def test_load_feed_bundle_loads_team_game_stats_from_website(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setenv(
        feed_ingestion.TEAM_GAME_STATS_WEBSITE_URL_ENV,
        "https://example.com/team-game-stats",
    )
    monkeypatch.setattr(
        feed_ingestion,
        "scrape_team_game_stats",
        lambda _url: [
            TeamGameStat(
                round=1,
                team="Rabbitohs",
                opponent="Roosters",
                points_for=20,
                points_against=18,
                result="W",
            )
        ],
    )

    bundle = feed_ingestion.load_feed_bundle()

    assert bundle.team_game_stats[0].team == "Rabbitohs"
    assert bundle.source_health["team_game_stats"]["status"] == "website"
