from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Literal, cast

from .data import FIXTURES, PLAYERS
from .models import (
    ByeRoundCoverage,
    CashGenerationOutlook,
    PlannerPlanRequest,
    PlannerPlanResponse,
    Player,
    RoundSimulation,
    ScenarioPlannerResult,
    SquadStructureScore,
    TradePair,
    TradeRecommendation,
    UserTeamImportRequest,
)


@dataclass
class StrategyConfig:
    risk_multiplier: float
    price_multiplier: float


STRATEGY_CONFIG: dict[str, StrategyConfig] = {
    "conservative": StrategyConfig(risk_multiplier=1.25, price_multiplier=0.9),
    "balanced": StrategyConfig(risk_multiplier=1.0, price_multiplier=1.0),
    "aggressive": StrategyConfig(risk_multiplier=0.85, price_multiplier=1.1),
}
PRICE_SENSITIVITY_FACTOR = 850
MOMENTUM_WEIGHT = 0.4


def project_player(player: Player) -> float:
    return (
        0.35 * player.season_average
        + 0.30 * player.last_3_average
        + 0.20 * player.minutes_adjusted_base
        + 0.10 * player.opponent_modifier
        + 0.05 * player.role_change_modifier
    )


def _can_cover_positions(out_players: tuple[Player, ...], in_players: tuple[Player, ...]) -> bool:
    for order in permutations(in_players, len(in_players)):
        if all(set(out.positions) & set(in_.positions) for out, in_ in zip(out_players, order)):
            return True
    return False


def _bye_coverage_score(players: tuple[Player, ...]) -> float:
    if not players:
        return 0.0
    return sum(1.0 / (1 + len(p.bye_rounds)) for p in players) / len(players)


def _risk_score(players: tuple[Player, ...], strategy: str) -> float:
    base = sum((p.role_risk + p.injury_risk + p.job_security_risk) for p in players)
    return base * STRATEGY_CONFIG[strategy].risk_multiplier


def _trade_score(
    out_players: tuple[Player, ...],
    in_players: tuple[Player, ...],
    strategy: str,
) -> tuple[float, float, int, float, float, float]:
    in_proj = sum(project_player(p) for p in in_players)
    out_proj = sum(project_player(p) for p in out_players)

    projected_gain_next_3 = (in_proj - out_proj) * 3
    projected_gain_next_6 = (in_proj - out_proj) * 6
    cash_impact = sum(out.price for out in out_players) - sum(in_.price for in_ in in_players)

    cash_generation_score = cash_impact / 10000
    bye_delta = _bye_coverage_score(in_players) - _bye_coverage_score(out_players)
    position_flex = sum(len(p.positions) for p in in_players) / max(len(in_players), 1)
    risk_score = _risk_score(in_players, strategy)

    trade_score = (
        (0.45 * projected_gain_next_3)
        + (0.25 * projected_gain_next_6)
        + (0.15 * cash_generation_score)
        + (0.10 * bye_delta)
        + (0.05 * position_flex)
        - (0.20 * risk_score)
    )

    return (
        projected_gain_next_3,
        projected_gain_next_6,
        cash_impact,
        bye_delta,
        risk_score,
        trade_score,
    )


def _player_index() -> dict[str, Player]:
    return {player.id: player for player in PLAYERS}


def recommend_trades(request: UserTeamImportRequest, top_n: int = 3) -> list[TradeRecommendation]:
    idx = _player_index()
    squad_players = [idx[player_id] for player_id in request.squad if player_id in idx]
    squad_ids = {player.id for player in squad_players}

    if request.must_sell:
        out_pool = [p for p in squad_players if p.id in request.must_sell and p.id not in request.locked_players]
    else:
        out_pool = sorted(
            [p for p in squad_players if p.id not in request.locked_players],
            key=project_player,
        )[: max(3, request.trades_available + 1)]

    in_pool = [p for p in PLAYERS if p.id not in squad_ids and p.status == "available"]

    max_trades = min(max(request.trades_available, 1), 3)

    # Collect best top_n recommendations per trade count so all groups are represented
    by_trade_count: dict[int, list[TradeRecommendation]] = {}

    for trade_count in range(1, max_trades + 1):
        if len(out_pool) < trade_count or len(in_pool) < trade_count:
            continue

        candidates: list[TradeRecommendation] = []
        for outs in combinations(out_pool, trade_count):
            for ins in combinations(in_pool, trade_count):
                cost = sum(i.price for i in ins) - sum(o.price for o in outs)
                if cost > request.bank:
                    continue
                if not _can_cover_positions(outs, ins):
                    continue

                (
                    gain_3,
                    gain_6,
                    cash_impact,
                    bye_delta,
                    risk_score,
                    trade_score,
                ) = _trade_score(outs, ins, request.strategy)

                risk_label = _risk_label(risk_score)
                cash_desc = f"${abs(cash_impact):,} {'freed' if cash_impact >= 0 else 'spent'}"
                candidates.append(
                    TradeRecommendation(
                        trade_count=trade_count,
                        trades=[
                            TradePair(out_player_id=out.id, in_player_id=ins[idx].id)
                            for idx, out in enumerate(outs)
                        ],
                        projected_gain_next_3=round(gain_3, 2),
                        projected_gain_next_6=round(gain_6, 2),
                        cash_impact=cash_impact,
                        bye_coverage_delta=round(bye_delta, 3),
                        risk_score=round(risk_score, 3),
                        total_trade_score=round(trade_score, 2),
                        explanation=(
                            f"Projected {gain_3:+.1f} pts over 3 rounds ({gain_6:+.1f} over 6). "
                            f"Cash impact: {cash_desc}. "
                            f"Risk: {risk_label} (score {risk_score:.2f}, strategy: {request.strategy})."
                        ),
                    )
                )

        candidates.sort(key=lambda rec: rec.total_trade_score, reverse=True)
        by_trade_count[trade_count] = candidates[:top_n]

    # Return all groups in order (1-trade first, then 2-trade, then 3-trade)
    result: list[TradeRecommendation] = []
    for tc in sorted(by_trade_count):
        result.extend(by_trade_count[tc])
    return result


def _risk_label(risk_score: float) -> str:
    if risk_score < 0.5:
        return "low"
    if risk_score < 1.0:
        return "medium"
    return "high"


def _upcoming_rounds(horizon: int) -> list[int]:
    rounds = sorted({fixture.round for fixture in FIXTURES})
    if not rounds:
        return list(range(1, horizon + 1))
    if len(rounds) >= horizon:
        return rounds[:horizon]
    last_round = rounds[-1]
    remaining = horizon - len(rounds)
    rounds.extend(range(last_round + 1, last_round + 1 + remaining))
    return rounds


def analyze_bye_coverage(players: list[Player], rounds: list[int]) -> list[ByeRoundCoverage]:
    coverage: list[ByeRoundCoverage] = []
    squad_size = max(len(players), 1)
    for round_number in rounds:
        bye_count = sum(1 for player in players if round_number in player.bye_rounds)
        available_count = len(players) - bye_count
        coverage.append(
            ByeRoundCoverage(
                round=round_number,
                available_count=available_count,
                bye_count=bye_count,
                coverage_ratio=round(available_count / squad_size, 3),
            )
        )
    return coverage


def _project_price_change(player: Player, strategy: str) -> int:
    projection = project_player(player)
    breakeven = player.breakeven if player.breakeven is not None else projection
    if len(player.price_history) >= 2:
        trend = player.price_history[-1].price - player.price_history[-2].price
    else:
        trend = 0
    strategy_scale = STRATEGY_CONFIG[strategy].price_multiplier
    # Scale projection-BE gap by price sensitivity and recent trend by momentum weight.
    raw_change = int(
        (
            (projection - breakeven) * PRICE_SENSITIVITY_FACTOR
            + trend * MOMENTUM_WEIGHT
        )
        * strategy_scale
    )
    return max(-50000, min(50000, raw_change))


def cash_generation_outlook(players: list[Player], strategy: str) -> CashGenerationOutlook:
    if not players:
        return CashGenerationOutlook(
            projected_price_change=0,
            projected_cash_generation=0,
            rising_players=[],
            falling_players=[],
            avg_breakeven_gap=0.0,
        )

    deltas = {player.id: _project_price_change(player, strategy) for player in players}
    projected_price_change = sum(deltas.values())
    avg_gap_sum = 0.0
    for player in players:
        projection = project_player(player)
        breakeven = player.breakeven if player.breakeven is not None else projection
        avg_gap_sum += projection - breakeven
    avg_gap = avg_gap_sum / len(players)
    rising_players = [player_id for player_id, delta in deltas.items() if delta > 0]
    falling_players = [player_id for player_id, delta in deltas.items() if delta < 0]
    rising_players.sort(key=lambda player_id: deltas[player_id], reverse=True)
    falling_players.sort(key=lambda player_id: deltas[player_id])

    return CashGenerationOutlook(
        projected_price_change=projected_price_change,
        projected_cash_generation=max(projected_price_change, 0),
        rising_players=rising_players[:5],
        falling_players=falling_players[:5],
        avg_breakeven_gap=round(avg_gap, 2),
    )


def squad_structure_score(players: list[Player]) -> SquadStructureScore:
    if not players:
        return SquadStructureScore(
            dual_position_count=0,
            position_counts={},
            position_flexibility_score=0.0,
            squad_balance_score=0.0,
        )

    position_counts: Counter[str] = Counter()
    dual_position_count = 0
    for player in players:
        if len(player.positions) > 1:
            dual_position_count += 1
        for position in player.positions:
            position_counts[position] += 1

    total_slots = sum(position_counts.values())
    ideal_share = 1 / len(position_counts)
    imbalance = 0.0
    for count in position_counts.values():
        share = count / total_slots
        imbalance += abs(share - ideal_share)

    flexibility_score = dual_position_count / len(players)
    balance_score = max(0.0, 1.0 - imbalance)
    return SquadStructureScore(
        dual_position_count=dual_position_count,
        position_counts=dict(sorted(position_counts.items())),
        position_flexibility_score=round(flexibility_score, 3),
        squad_balance_score=round(balance_score, 3),
    )


def _apply_trades_to_squad(squad_ids: list[str], trades: list[TradePair]) -> list[str]:
    next_squad = list(squad_ids)
    for trade in trades:
        if trade.out_player_id in next_squad:
            next_squad.remove(trade.out_player_id)
        if trade.in_player_id not in next_squad:
            next_squad.append(trade.in_player_id)
    return next_squad


def _simulate_scenario(
    request: PlannerPlanRequest,
    scenario: Literal["conservative", "balanced", "aggressive"],
) -> ScenarioPlannerResult:
    rounds = _upcoming_rounds(request.planning_horizon)
    current_squad = list(request.squad)
    current_bank = request.bank
    simulations: list[RoundSimulation] = []

    for round_number in rounds:
        simulation_request = UserTeamImportRequest(
            squad=current_squad,
            bank=max(current_bank, 0),
            trades_available=request.trades_available,
            boosts_available=request.boosts_available,
            strategy=scenario,
            locked_players=[p for p in request.locked_players if p in current_squad],
            must_sell=[p for p in request.must_sell if p in current_squad],
        )
        recommendation = next(iter(recommend_trades(simulation_request, top_n=1)), None)
        if recommendation is None:
            simulations.append(
                RoundSimulation(
                    round=round_number,
                    trades=[],
                    projected_points_delta=0.0,
                    projected_cash_delta=0,
                    bank_after=current_bank,
                    risk_score=0.0,
                )
            )
            continue

        current_squad = _apply_trades_to_squad(current_squad, recommendation.trades)
        current_bank += recommendation.cash_impact
        simulations.append(
            RoundSimulation(
                round=round_number,
                trades=recommendation.trades,
                projected_points_delta=recommendation.projected_gain_next_3,
                projected_cash_delta=recommendation.cash_impact,
                bank_after=current_bank,
                risk_score=recommendation.risk_score,
            )
        )

    idx = _player_index()
    squad_players = [idx[player_id] for player_id in request.squad if player_id in idx]
    bye_coverage = analyze_bye_coverage(squad_players, rounds)
    structure = squad_structure_score(squad_players)
    total_points = sum(item.projected_points_delta for item in simulations)
    total_cash = sum(item.projected_cash_delta for item in simulations)
    avg_risk = (
        sum(item.risk_score for item in simulations) / len(simulations) if simulations else 0.0
    )
    avg_coverage = (
        sum(item.coverage_ratio for item in bye_coverage) / len(bye_coverage) if bye_coverage else 0.0
    )

    return ScenarioPlannerResult(
        scenario=scenario,
        rounds=simulations,
        total_projected_points_delta=round(total_points, 2),
        total_projected_cash_delta=total_cash,
        avg_risk_score=round(avg_risk, 3),
        bye_coverage_score=round(avg_coverage, 3),
        position_flexibility_score=structure.position_flexibility_score,
    )


def build_planner_plan(request: PlannerPlanRequest) -> PlannerPlanResponse:
    rounds = _upcoming_rounds(request.planning_horizon)
    idx = _player_index()
    squad_players = [idx[player_id] for player_id in request.squad if player_id in idx]
    scenarios: list[Literal["conservative", "balanced", "aggressive"]] = (
        cast(list[Literal["conservative", "balanced", "aggressive"]], list(STRATEGY_CONFIG.keys()))
        if request.compare_all_scenarios
        else [request.strategy]
    )
    scenario_results = [_simulate_scenario(request, scenario) for scenario in scenarios]
    return PlannerPlanResponse(
        planning_horizon=request.planning_horizon,
        bye_coverage=analyze_bye_coverage(squad_players, rounds),
        cash_generation=cash_generation_outlook(squad_players, request.strategy),
        squad_structure=squad_structure_score(squad_players),
        scenarios=scenario_results,
    )
