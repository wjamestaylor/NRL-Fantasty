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
    breakeven: int | None = None
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
    confidence: Literal["low", "medium", "high"] = "medium"
    category: str = "general"
    impact_score: float = 0.0
    sentiment: str | None = None
    availability_status: str | None = None
    round: int | None = None
    source: str | None = None
    details: str | None = None


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
    trade_count: int
    trades: list[TradePair]
    projected_gain_next_3: float
    projected_gain_next_6: float
    cash_impact: int
    bye_coverage_delta: float
    risk_score: float
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_label: Literal["low", "medium", "high"]
    news_flags: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    total_trade_score: float
    explanation: str


class TradeRecommendationResponse(BaseModel):
    recommendations: list[TradeRecommendation]


class TradeSimulationRequest(BaseModel):
    team: UserTeamImportRequest
    trades: list[TradePair]


class ByeRoundCoverage(BaseModel):
    round: int
    available_count: int = Field(ge=0)
    bye_count: int = Field(ge=0)
    coverage_ratio: float


class CashGenerationOutlook(BaseModel):
    projected_price_change: int
    projected_cash_generation: int
    rising_players: list[str]
    falling_players: list[str]
    avg_breakeven_gap: float


class SquadStructureScore(BaseModel):
    dual_position_count: int = Field(ge=0)
    position_counts: dict[str, int]
    position_flexibility_score: float
    squad_balance_score: float


class RoundSimulation(BaseModel):
    round: int
    trades: list[TradePair]
    projected_points_delta: float
    projected_cash_delta: int
    bank_after: int
    risk_score: float


class ScenarioPlannerResult(BaseModel):
    scenario: Literal["conservative", "balanced", "aggressive"]
    rounds: list[RoundSimulation]
    total_projected_points_delta: float
    total_projected_cash_delta: int
    avg_risk_score: float
    bye_coverage_score: float
    position_flexibility_score: float


class PlannerPlanRequest(UserTeamImportRequest):
    planning_horizon: int = Field(default=3, ge=1, le=6)
    compare_all_scenarios: bool = False


class PlannerPlanResponse(BaseModel):
    planning_horizon: int
    bye_coverage: list[ByeRoundCoverage]
    cash_generation: CashGenerationOutlook
    squad_structure: SquadStructureScore
    scenarios: list[ScenarioPlannerResult]
