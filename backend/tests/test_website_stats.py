from app import website_stats


def test_scrape_player_stats_parses_html_table(monkeypatch) -> None:
    html = """
    <table>
      <tr><th>Player</th><th>Team</th><th>Pos</th><th>Price</th><th>Avg</th><th>Last 3</th><th>Minutes</th></tr>
      <tr><td>Cameron Murray</td><td>Rabbitohs</td><td>MID</td><td>$760,000</td><td>60.8</td><td>63.0</td><td>61</td></tr>
    </table>
    """
    monkeypatch.setattr(website_stats, "_fetch_html", lambda _url: html)

    players = website_stats.scrape_player_stats("https://example.com/players")

    assert len(players) == 1
    assert players[0].name == "Cameron Murray"
    assert players[0].team == "Rabbitohs"
    assert players[0].season_average == 60.8


def test_scrape_team_game_stats_parses_html_table(monkeypatch) -> None:
    html = """
    <table>
      <tr><th>Round</th><th>Team</th><th>Opponent</th><th>For</th><th>Against</th></tr>
      <tr><td>1</td><td>Rabbitohs</td><td>Roosters</td><td>20</td><td>18</td></tr>
    </table>
    """
    monkeypatch.setattr(website_stats, "_fetch_html", lambda _url: html)

    records = website_stats.scrape_team_game_stats("https://example.com/team-game-stats")

    assert len(records) == 1
    assert records[0].team == "Rabbitohs"
    assert records[0].result == "W"
