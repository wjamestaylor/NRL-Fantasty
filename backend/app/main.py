from fastapi import FastAPI, HTTPException

from .archive import VALID_DATASETS as _VALID_DATASETS
from .archive import list_archived_dates, load_archived_snapshot
from .data import DATA_LOADED_AT, DATA_SOURCE_HEALTH, FIXTURES, NEWS_SIGNALS, PLAYERS
from .engine import project_player, recommend_trades
from .feed_ingestion import DEFAULT_DATA_DIR
from .models import (
    TradeRecommendationResponse,
    TradeSimulationRequest,
    UserTeamImportRequest,
)

app = FastAPI(title="Fantasy NRL Trade Lab API", version="0.1.0")


def _rolling_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return round(sum(values[-window:]) / window, 2)


def _player_analytics_payload(player_id: str) -> dict:
    for player in PLAYERS:
        if player.id != player_id:
            continue

        ordered_games = sorted(player.game_details, key=lambda game: game.round)
        scores = [game.score for game in ordered_games]
        minutes = [game.minutes for game in ordered_games]
        base_projection = project_player(player)

        return {
            "id": player.id,
            "name": player.name,
            "team": player.team,
            "positions": player.positions,
            "price": player.price,
            "price_history": [point.model_dump() for point in player.price_history],
            "season_average": player.season_average,
            "rolling_scores": {
                "last_3": _rolling_average(scores, 3),
                "last_5": _rolling_average(scores, 5),
            },
            "minutes": {
                "recent": minutes[-5:],
                "average": round(sum(minutes) / len(minutes), 2) if minutes else None,
            },
            "projections": {
                "next_round": round(base_projection, 2),
                "next_3_rounds": round(base_projection * 3, 2),
                "next_6_rounds": round(base_projection * 6, 2),
                "season_remaining": round(base_projection * 20, 2),
            },
        }

    raise HTTPException(status_code=404, detail="Player not found")


@app.get("/players")
def get_players() -> list[dict]:
    return [player.model_dump(exclude_none=True) for player in PLAYERS]


@app.get("/players/analytics")
def get_player_analytics() -> list[dict]:
    return [_player_analytics_payload(player.id) for player in PLAYERS]


@app.get("/players/{player_id}")
def get_player(player_id: str) -> dict:
    for player in PLAYERS:
        if player.id == player_id:
            return player.model_dump(exclude_none=True)
    raise HTTPException(status_code=404, detail="Player not found")


@app.get("/players/{player_id}/analytics")
def get_player_analytics_by_id(player_id: str) -> dict:
    return _player_analytics_payload(player_id)


@app.get("/fixtures")
def get_fixtures() -> list[dict]:
    return [fixture.model_dump() for fixture in FIXTURES]


@app.get("/news/signals")
def get_news_signals() -> list[dict]:
    return [signal.model_dump() for signal in NEWS_SIGNALS]


@app.post("/user-team/import")
def import_user_team(payload: UserTeamImportRequest) -> dict:
    return {
        "message": "Team imported",
        "team": payload.model_dump(),
    }


@app.post("/trade/recommend", response_model=TradeRecommendationResponse)
def post_trade_recommend(payload: UserTeamImportRequest) -> TradeRecommendationResponse:
    return TradeRecommendationResponse(recommendations=recommend_trades(payload))


@app.post("/trade/simulate")
def post_trade_simulate(payload: TradeSimulationRequest) -> dict:
    current_request = payload.team
    recommendations = recommend_trades(current_request, top_n=50)

    requested_pairs = {(t.out_player_id, t.in_player_id) for t in payload.trades}
    for recommendation in recommendations:
        rec_pairs = {(t.out_player_id, t.in_player_id) for t in recommendation.trades}
        if rec_pairs == requested_pairs:
            return {
                "simulation": recommendation.model_dump(),
                "strategy": current_request.strategy,
            }

    raise HTTPException(status_code=400, detail="Trade combination is not legal for this team/bank")


@app.get("/planner/bye")
def get_bye_planner() -> dict:
    bye_map: dict[int, list[str]] = {}
    for player in PLAYERS:
        for bye_round in player.bye_rounds:
            bye_map.setdefault(bye_round, []).append(player.id)
    return {"bye_rounds": bye_map}


@app.get("/health/data-sources")
def get_data_source_health() -> dict:
    source_statuses = [source["status"] for source in DATA_SOURCE_HEALTH.values()]
    status = "degraded" if any(state == "snapshot_fallback" for state in source_statuses) else "ok"
    breakeven_enabled = DATA_SOURCE_HEALTH["players"].get("breakeven_status") == "enabled"
    return {
        "status": status,
        "loaded_at": DATA_LOADED_AT,
        "sources": DATA_SOURCE_HEALTH,
        "features": {
            "player_breakeven": {
                "enabled": breakeven_enabled,
                "reason": DATA_SOURCE_HEALTH["players"].get("breakeven_reason"),
                "coverage": DATA_SOURCE_HEALTH["players"].get("breakeven_coverage"),
            }
        },
    }


@app.get("/history/snapshots")
def get_history_snapshots() -> dict:
    """List available archived snapshot dates for all datasets."""
    return {
        dataset: list_archived_dates(DEFAULT_DATA_DIR, dataset)
        for dataset in _VALID_DATASETS
    }


@app.get("/history/snapshots/{dataset}/{snapshot_date}")
def get_history_snapshot(dataset: str, snapshot_date: str) -> list:
    """Return the archived snapshot payload for *dataset* on *snapshot_date* (YYYY-MM-DD)."""
    try:
        return load_archived_snapshot(DEFAULT_DATA_DIR, dataset, snapshot_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
