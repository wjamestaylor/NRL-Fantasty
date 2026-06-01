from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations

from .data import PLAYERS
from .models import Player, TradePair, TradeRecommendation, UserTeamImportRequest


@dataclass
class StrategyConfig:
    risk_multiplier: float


STRATEGY_CONFIG: dict[str, StrategyConfig] = {
    "conservative": StrategyConfig(risk_multiplier=1.25),
    "balanced": StrategyConfig(risk_multiplier=1.0),
    "aggressive": StrategyConfig(risk_multiplier=0.85),
}


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
                            TradePair(out_player_id=out.id, in_player_id=ins[i].id)
                            for i, out in enumerate(outs)
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
