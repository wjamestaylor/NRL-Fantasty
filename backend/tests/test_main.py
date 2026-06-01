from fastapi.testclient import TestClient

from app.main import app


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


def test_health_ingestion_log_respects_limit_parameter() -> None:
    response = client.get("/health/ingestion-log?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) <= 5

