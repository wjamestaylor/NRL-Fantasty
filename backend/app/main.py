from fastapi import FastAPI, HTTPException

from .data import DATA_LOADED_AT, DATA_SOURCE_HEALTH, FIXTURES, NEWS_SIGNALS, PLAYERS
from .engine import recommend_trades
from .models import (
    TradeRecommendationResponse,
    TradeSimulationRequest,
    UserTeamImportRequest,
)

app = FastAPI(title="Fantasy NRL Trade Lab API", version="0.1.0")


@app.get("/players")
def get_players() -> list[dict]:
    return [player.model_dump() for player in PLAYERS]


@app.get("/players/{player_id}")
def get_player(player_id: str) -> dict:
    for player in PLAYERS:
        if player.id == player_id:
            return player.model_dump()
    raise HTTPException(status_code=404, detail="Player not found")


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
    source_states = [source["status"] for source in DATA_SOURCE_HEALTH.values()]
    status = "degraded" if any(state == "snapshot_fallback" for state in source_states) else "ok"
    return {
        "status": status,
        "loaded_at": DATA_LOADED_AT,
        "sources": DATA_SOURCE_HEALTH,
    }
