import app.engine as engine
from app.engine import (
    _trade_news_intelligence,
    _risk_label,
    build_planner_plan,
    cash_generation_outlook,
    project_player,
    recommend_trades,
    squad_structure_score,
)
from app.models import NewsSignal, PlannerPlanRequest, Player, UserTeamImportRequest


def test_projection_formula_matches_v1_weights() -> None:
    player = Player(
        id="T1",
        name="Test",
        team="X",
        positions=["MID"],
        price=100000,
        season_average=50,
        last_3_average=40,
        minutes_adjusted_base=60,
        opponent_modifier=2,
        role_change_modifier=4,
        role_risk=0.1,
        injury_risk=0.1,
        job_security_risk=0.1,
        bye_rounds=[],
    )

    projection = project_player(player)

    assert round(projection, 2) == 41.9


def test_recommend_trades_respects_bank_and_positions() -> None:
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=100000,
        trades_available=1,
        boosts_available=0,
        strategy="balanced",
        locked_players=["P1"],
        must_sell=["P3"],
    )

    recommendations = recommend_trades(request)

    assert recommendations
    best = recommendations[0]
    assert best.trades[0].out_player_id == "P3"

    assert best.cash_impact >= -request.bank


def test_recommend_trades_populates_trade_count() -> None:
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=500000,
        trades_available=2,
        boosts_available=0,
        strategy="balanced",
    )

    recommendations = recommend_trades(request)

    assert recommendations
    for rec in recommendations:
        assert rec.trade_count == len(rec.trades)


def test_recommend_trades_groups_by_trade_count() -> None:
    """Results are ordered 1-trade first, then 2-trade."""
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=500000,
        trades_available=2,
        boosts_available=0,
        strategy="balanced",
    )

    recommendations = recommend_trades(request)

    assert recommendations
    seen_counts = [rec.trade_count for rec in recommendations]
    # Trade counts should appear in non-decreasing order (1s before 2s before 3s)
    assert seen_counts == sorted(seen_counts)
    # At least one 1-trade recommendation expected
    assert any(rec.trade_count == 1 for rec in recommendations)


def test_recommend_trades_locked_players_never_traded_out() -> None:
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=500000,
        trades_available=2,
        boosts_available=0,
        strategy="balanced",
        locked_players=["P1", "P2"],
    )

    recommendations = recommend_trades(request)

    for rec in recommendations:
        out_ids = {t.out_player_id for t in rec.trades}
        assert "P1" not in out_ids, "Locked player P1 must not appear as an outgoing trade"
        assert "P2" not in out_ids, "Locked player P2 must not appear as an outgoing trade"


def test_recommend_trades_must_sell_always_traded_out() -> None:
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=500000,
        trades_available=2,
        boosts_available=0,
        strategy="balanced",
        must_sell=["P3"],
    )

    recommendations = recommend_trades(request)

    assert recommendations
    for rec in recommendations:
        out_ids = {t.out_player_id for t in rec.trades}
        assert "P3" in out_ids, "must_sell player P3 must appear in every outgoing trade set"


def test_recommend_trades_explanation_includes_risk_and_strategy() -> None:
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=500000,
        trades_available=1,
        boosts_available=0,
        strategy="aggressive",
        must_sell=["P3"],
    )

    recommendations = recommend_trades(request)

    assert recommendations
    explanation = recommendations[0].explanation
    assert "aggressive" in explanation
    assert "pts" in explanation
    assert "Cash impact" in explanation
    assert "Confidence:" in explanation


def test_recommend_trades_includes_phase5_confidence_and_flags() -> None:
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=500000,
        trades_available=1,
        boosts_available=0,
        strategy="balanced",
        must_sell=["P3"],
    )

    recommendations = recommend_trades(request)

    assert recommendations
    rec = recommendations[0]
    assert 0.0 <= rec.confidence_score <= 1.0
    assert rec.confidence_label in {"low", "medium", "high"}
    assert isinstance(rec.news_flags, list)
    assert isinstance(rec.risk_flags, list)


def test_recommend_trades_budget_constraint_respected() -> None:
    request = UserTeamImportRequest(
        squad=["P1", "P2", "P3"],
        bank=0,
        trades_available=1,
        boosts_available=0,
        strategy="balanced",
    )

    recommendations = recommend_trades(request)

    # With zero bank, every recommendation can only bring in players cheaper than traded-out ones
    for rec in recommendations:
        assert rec.cash_impact >= 0, "With zero bank, trades must be cash-neutral or cash-positive"


def test_risk_label_thresholds() -> None:
    assert _risk_label(0.0) == "low"
    assert _risk_label(0.49) == "low"
    assert _risk_label(0.5) == "medium"
    assert _risk_label(0.99) == "medium"
    assert _risk_label(1.0) == "high"
    assert _risk_label(2.5) == "high"


def test_cash_generation_outlook_returns_risers_and_fallers() -> None:
    player_up = Player(
        id="UP",
        name="Riser",
        team="A",
        positions=["MID"],
        price=500000,
        season_average=58,
        last_3_average=60,
        minutes_adjusted_base=59,
        opponent_modifier=2,
        role_change_modifier=1,
        role_risk=0.1,
        injury_risk=0.1,
        job_security_risk=0.1,
        breakeven=35,
        price_history=[{"round": 1, "price": 480000}, {"round": 2, "price": 500000}],
    )
    player_down = Player(
        id="DOWN",
        name="Faller",
        team="B",
        positions=["EDG"],
        price=520000,
        season_average=42,
        last_3_average=39,
        minutes_adjusted_base=40,
        opponent_modifier=-1,
        role_change_modifier=-2,
        role_risk=0.3,
        injury_risk=0.3,
        job_security_risk=0.2,
        breakeven=60,
        price_history=[{"round": 1, "price": 540000}, {"round": 2, "price": 520000}],
    )

    outlook = cash_generation_outlook([player_up, player_down], "balanced")

    assert "UP" in outlook.rising_players
    assert "DOWN" in outlook.falling_players
    assert outlook.projected_price_change != 0


def test_build_planner_plan_can_compare_all_scenarios() -> None:
    request = PlannerPlanRequest(
        squad=["P1", "P2", "P3", "P4"],
        bank=200000,
        trades_available=2,
        boosts_available=1,
        strategy="balanced",
        planning_horizon=3,
        compare_all_scenarios=True,
    )

    plan = build_planner_plan(request)

    assert plan.planning_horizon == 3
    assert len(plan.bye_coverage) == 3
    assert plan.cash_generation.avg_breakeven_gap is not None
    assert plan.squad_structure.position_flexibility_score >= 0
    assert {scenario.scenario for scenario in plan.scenarios} == {
        "conservative",
        "balanced",
        "aggressive",
    }
    assert all(len(scenario.rounds) == 3 for scenario in plan.scenarios)


def test_squad_structure_score_counts_dual_positions() -> None:
    structure = squad_structure_score(
        [
            Player(
                id="A",
                name="Dual",
                team="A",
                positions=["MID", "EDG"],
                price=400000,
                season_average=45,
                last_3_average=46,
                minutes_adjusted_base=45,
                opponent_modifier=0,
                role_change_modifier=0,
                role_risk=0.1,
                injury_risk=0.1,
                job_security_risk=0.1,
            ),
            Player(
                id="B",
                name="Single",
                team="A",
                positions=["HOK"],
                price=430000,
                season_average=48,
                last_3_average=47,
                minutes_adjusted_base=46,
                opponent_modifier=0,
                role_change_modifier=0,
                role_risk=0.1,
                injury_risk=0.1,
                job_security_risk=0.1,
            ),
        ]
    )

    assert structure.dual_position_count == 1
    assert structure.position_counts["MID"] == 1
    assert structure.position_counts["HOK"] == 1


def test_trade_news_intelligence_processes_signals_and_computes_confidence(monkeypatch) -> None:
    in_player = Player(
        id="IN1",
        name="Incoming",
        team="Broncos",
        positions=["HLF"],
        price=700000,
        season_average=60,
        last_3_average=62,
        minutes_adjusted_base=60,
        opponent_modifier=2,
        role_change_modifier=3,
        role_risk=0.1,
        injury_risk=0.05,
        job_security_risk=0.05,
    )
    out_player = Player(
        id="OUT1",
        name="Outgoing",
        team="Raiders",
        positions=["HLF"],
        price=700000,
        season_average=58,
        last_3_average=54,
        minutes_adjusted_base=55,
        opponent_modifier=0,
        role_change_modifier=-2,
        role_risk=0.2,
        injury_risk=0.2,
        job_security_risk=0.15,
    )
    monkeypatch.setattr(
        engine,
        "NEWS_SIGNALS",
        [
            NewsSignal(
                player_id="IN1",
                signal="named in starting side",
                confidence="high",
                category="team_list",
                sentiment="positive",
                availability_status="available",
            ),
            NewsSignal(
                player_id="IN1",
                signal="coach quote boost",
                confidence="medium",
                category="coach_sentiment",
                sentiment="positive",
            ),
            NewsSignal(
                player_id="OUT1",
                signal="hamstring injury concern",
                confidence="high",
                category="injury",
                availability_status="out",
            ),
        ],
    )

    confidence_score, confidence_label, news_flags, risk_flags, _adjustment = _trade_news_intelligence(
        (out_player,),
        (in_player,),
    )

    assert confidence_score > 0.5
    assert confidence_label in {"medium", "high"}
    assert any("team list: named" in flag for flag in news_flags)
    assert any("coach sentiment positive" in flag for flag in news_flags)
    assert any("origin watchlist" in flag for flag in risk_flags)
