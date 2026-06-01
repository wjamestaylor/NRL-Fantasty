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
