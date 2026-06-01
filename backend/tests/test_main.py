from fastapi.testclient import TestClient

from app.main import app
from app import user_store


client = TestClient(app)


def test_players_analytics_endpoint_returns_enriched_payload() -> None:
    response = client.get("/players/analytics")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert "price_history" in payload[0]
    assert "rolling_scores" in payload[0]
    assert "minutes" in payload[0]
    assert "projections" in payload[0]


def test_player_analytics_endpoint_returns_single_player_payload() -> None:
    response = client.get("/players/P1/analytics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "P1"
    assert "next_3_rounds" in payload["projections"]


def test_history_snapshots_endpoint_lists_datasets() -> None:
    response = client.get("/history/snapshots")

    assert response.status_code == 200
    payload = response.json()
    assert "players" in payload
    assert "fixtures" in payload
    assert "news" in payload
    for dates in payload.values():
        assert isinstance(dates, list)


def test_history_snapshot_detail_returns_404_for_missing_date() -> None:
    response = client.get("/history/snapshots/players/2000-01-01")
    assert response.status_code == 404


def test_history_snapshot_detail_returns_422_for_bad_date() -> None:
    response = client.get("/history/snapshots/players/not-a-date")
    assert response.status_code == 422


def test_history_snapshot_detail_returns_422_for_unknown_dataset() -> None:
    response = client.get("/history/snapshots/unknown_dataset/2024-01-01")
    assert response.status_code == 422


def test_health_data_sources_returns_required_fields() -> None:
    response = client.get("/health/data-sources")

    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload
    assert "loaded_at" in payload
    assert "alerts" in payload
    assert isinstance(payload["alerts"], list)
    assert "sources" in payload
    assert "features" in payload
    assert "player_breakeven" in payload["features"]


def test_health_live_and_ready_endpoints_return_operational_payloads() -> None:
    live_response = client.get("/health/live")
    ready_response = client.get("/health/ready")

    assert live_response.status_code == 200
    assert live_response.json() == {"status": "ok"}

    assert ready_response.status_code == 200
    payload = ready_response.json()
    assert payload["status"] == "ready"
    assert payload["player_count"] > 0
    assert payload["fixture_count"] > 0


def test_health_data_sources_sources_include_monitoring_fields() -> None:
    response = client.get("/health/data-sources")

    assert response.status_code == 200
    payload = response.json()
    for _name, source_info in payload["sources"].items():
        assert "status" in source_info
        assert "record_count" in source_info
        assert "ingested_at" in source_info


def test_health_ingestion_log_returns_list() -> None:
    response = client.get("/health/ingestion-log")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_trade_recommend_endpoint_returns_grouped_recommendations() -> None:
    payload = {
        "squad": ["P1", "P2", "P3"],
        "bank": 500000,
        "trades_available": 2,
        "boosts_available": 1,
        "strategy": "balanced",
        "locked_players": ["P1"],
        "must_sell": ["P3"],
    }

    response = client.post("/trade/recommend", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert data["recommendations"]

    for rec in data["recommendations"]:
        assert "trade_count" in rec
        assert "trades" in rec
        assert "projected_gain_next_3" in rec
        assert "cash_impact" in rec
        assert "confidence_score" in rec
        assert "confidence_label" in rec
        assert "news_flags" in rec
        assert "risk_flags" in rec
        assert "explanation" in rec
        # Locked player P1 must never be traded out
        out_ids = {t["out_player_id"] for t in rec["trades"]}
        assert "P1" not in out_ids
        # must_sell P3 always traded out
        assert "P3" in out_ids


def test_news_signals_endpoint_returns_phase5_fields() -> None:
    response = client.get("/news/signals")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    first = payload[0]
    assert "player_id" in first
    assert "signal" in first
    assert "confidence" in first
    assert "category" in first
    assert "impact_score" in first


def test_team_game_stats_endpoint_returns_list() -> None:
    response = client.get("/teams/game-stats")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_trade_recommend_endpoint_rejects_invalid_trades_available() -> None:
    payload = {
        "squad": ["P1"],
        "bank": 100000,
        "trades_available": 5,  # exceeds maximum of 3
        "boosts_available": 0,
        "strategy": "balanced",
    }

    response = client.post("/trade/recommend", json=payload)

    assert response.status_code == 422


def test_trade_recommend_endpoint_with_zero_bank_only_free_moves() -> None:
    payload = {
        "squad": ["P1", "P2", "P3"],
        "bank": 0,
        "trades_available": 1,
        "boosts_available": 0,
        "strategy": "conservative",
    }

    response = client.post("/trade/recommend", json=payload)

    assert response.status_code == 200
    data = response.json()
    for rec in data["recommendations"]:
        assert rec["cash_impact"] >= 0


def test_trade_simulate_returns_phase5_fields_for_valid_trade() -> None:
    team_payload = {
        "squad": ["P1", "P2", "P3"],
        "bank": 500000,
        "trades_available": 1,
        "boosts_available": 0,
        "strategy": "balanced",
        "must_sell": ["P3"],
    }
    rec_response = client.post("/trade/recommend", json=team_payload)
    assert rec_response.status_code == 200
    recommendation = rec_response.json()["recommendations"][0]

    sim_response = client.post(
        "/trade/simulate",
        json={
            "team": team_payload,
            "trades": recommendation["trades"],
        },
    )

    assert sim_response.status_code == 200
    simulation = sim_response.json()["simulation"]
    assert "confidence_score" in simulation
    assert "confidence_label" in simulation
    assert "news_flags" in simulation
    assert "risk_flags" in simulation


def test_planner_bye_endpoint_returns_round_mapping() -> None:
    response = client.get("/planner/bye")

    assert response.status_code == 200
    payload = response.json()
    assert "bye_rounds" in payload
    assert isinstance(payload["bye_rounds"], dict)


def test_planner_plan_endpoint_returns_phase4_payload() -> None:
    payload = {
        "squad": ["P1", "P2", "P3", "P4"],
        "bank": 200000,
        "trades_available": 2,
        "boosts_available": 1,
        "strategy": "balanced",
        "planning_horizon": 3,
        "compare_all_scenarios": True,
    }

    response = client.post("/planner/plan", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["planning_horizon"] == 3
    assert len(data["bye_coverage"]) == 3
    assert "projected_cash_generation" in data["cash_generation"]
    assert "position_flexibility_score" in data["squad_structure"]
    scenarios = {scenario["scenario"] for scenario in data["scenarios"]}
    assert scenarios == {"conservative", "balanced", "aggressive"}
    assert all(len(scenario["rounds"]) == 3 for scenario in data["scenarios"])


def test_auth_register_login_and_saved_teams_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(user_store, "STORE_PATH", tmp_path / "user_store.json")

    register_response = client.post(
        "/auth/register",
        json={
            "email": "coach@example.com",
            "password": "securepass",
            "display_name": "Coach",
        },
    )
    assert register_response.status_code == 200
    register_payload = register_response.json()
    assert register_payload["user"]["email"] == "coach@example.com"
    token = register_payload["token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer " + token},
    )
    assert me_response.status_code == 200
    assert me_response.json()["display_name"] == "Coach"

    save_response = client.post(
        "/user-teams",
        headers={"Authorization": "Bearer " + token},
        json={
            "name": "Round 12 setup",
            "notes": "Balanced buy targets",
            "team": {
                "squad": ["P1", "P2", "P3"],
                "bank": 175000,
                "trades_available": 2,
                "boosts_available": 1,
                "strategy": "balanced",
                "locked_players": ["P1"],
                "must_sell": ["P3"],
                "planning_horizon": 4,
                "compare_all_scenarios": True,
            },
        },
    )
    assert save_response.status_code == 200
    assert save_response.json()["team"]["planning_horizon"] == 4

    login_response = client.post(
        "/auth/login",
        json={"email": "coach@example.com", "password": "securepass"},
    )
    assert login_response.status_code == 200
    login_token = login_response.json()["token"]

    list_response = client.get(
        "/user-teams",
        headers={"Authorization": "Bearer " + login_token},
    )
    assert list_response.status_code == 200
    teams = list_response.json()
    assert len(teams) == 1
    assert teams[0]["name"] == "Round 12 setup"
    assert teams[0]["team"]["locked_players"] == ["P1"]


def test_saved_teams_require_authentication(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(user_store, "STORE_PATH", tmp_path / "user_store.json")

    response = client.get("/user-teams")

    assert response.status_code == 401
