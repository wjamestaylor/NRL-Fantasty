from app.engine import project_player, recommend_trades
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
