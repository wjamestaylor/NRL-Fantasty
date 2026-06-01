from app.engine import _risk_label, project_player, recommend_trades
from app.models import Player, UserTeamImportRequest


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
