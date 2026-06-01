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
