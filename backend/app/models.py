from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlayerPricePoint(BaseModel):
    round: int = Field(ge=1)
    price: int = Field(ge=0)


class PlayerGameDetail(BaseModel):
    round: int = Field(ge=1)
    score: float
    minutes: int = Field(ge=0, le=80)


class Player(BaseModel):
    id: str
    name: str
    team: str
    positions: list[str]
    price: int
    season_average: float
    last_3_average: float
    minutes_adjusted_base: float
    opponent_modifier: float
    role_change_modifier: float
    role_risk: float
    injury_risk: float
    job_security_risk: float
    bye_rounds: list[int] = Field(default_factory=list)
    status: str = "available"
    price_history: list[PlayerPricePoint] = Field(default_factory=list)
    game_details: list[PlayerGameDetail] = Field(default_factory=list)


class Fixture(BaseModel):
    round: int
    home_team: str
    away_team: str


class NewsSignal(BaseModel):
    player_id: str
    signal: str
    confidence: Literal["low", "medium", "high"]


class UserTeamImportRequest(BaseModel):
    squad: list[str]
    bank: int = Field(ge=0)
    trades_available: int = Field(ge=0, le=3)
    boosts_available: int = Field(ge=0)
    strategy: Literal["conservative", "balanced", "aggressive"] = "balanced"
    locked_players: list[str] = Field(default_factory=list)
    must_sell: list[str] = Field(default_factory=list)


class TradePair(BaseModel):
    out_player_id: str
    in_player_id: str


class TradeRecommendation(BaseModel):
    trades: list[TradePair]
    projected_gain_next_3: float
    projected_gain_next_6: float
    cash_impact: int
    bye_coverage_delta: float
    risk_score: float
    total_trade_score: float
    explanation: str


class TradeRecommendationResponse(BaseModel):
    recommendations: list[TradeRecommendation]


class TradeSimulationRequest(BaseModel):
    team: UserTeamImportRequest
    trades: list[TradePair]
