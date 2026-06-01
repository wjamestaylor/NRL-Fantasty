from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

import httpx

from .models import Player, TeamGameStat


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._current_table = []
            return
        if self._current_table is None:
            return
        if tag == "tr":
            self._current_row = []
            return
        if tag in {"td", "th"} and self._current_row is not None:
            self._cell_parts = []
            return
        if tag == "br" and self._cell_parts is not None:
            self._cell_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell_parts is not None and self._current_row is not None:
            cell = " ".join("".join(self._cell_parts).split())
            self._current_row.append(cell)
            self._cell_parts = None
            return
        if tag == "tr" and self._current_table is not None and self._current_row is not None:
            if any(cell.strip() for cell in self._current_row):
                self._current_table.append(self._current_row)
            self._current_row = None
            return
        if tag == "table" and self._current_table is not None:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = None


def _fetch_html(url: str) -> str:
    timeout = httpx.Timeout(15.0, connect=5.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _parse_number(value: Any, *, target_type: type[int] | type[float], default: int | float) -> int | float:
    if value is None:
        return default
    cleaned = re.sub(r"[^0-9.+-]", "", str(value))
    if not cleaned:
        return default
    try:
        return target_type(cleaned)
    except ValueError:
        return default


def _find_header_key(row: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in row:
            return candidate
    return None


def _tables_as_rows(html: str) -> list[list[dict[str, str]]]:
    parser = _TableParser()
    parser.feed(html)
    parsed_tables: list[list[dict[str, str]]] = []
    for table in parser.tables:
        if len(table) < 2:
            continue
        headers = [_normalize_header(header) for header in table[0]]
        if not headers:
            continue
        rows: list[dict[str, str]] = []
        for raw_row in table[1:]:
            values = raw_row + [""] * (len(headers) - len(raw_row))
            row = {header: values[index] for index, header in enumerate(headers)}
            rows.append(row)
        parsed_tables.append(rows)
    return parsed_tables


def _player_id(name: str, team: str) -> str:
    seed = re.sub(r"[^a-z0-9]", "", f"{name}-{team}".lower())
    return seed or "unknown-player"


def scrape_player_stats(url: str) -> list[Player]:
    html = _fetch_html(url)
    tables = _tables_as_rows(html)
    players: list[Player] = []
    for rows in tables:
        if not rows:
            continue
        sample = rows[0]
        has_name = _find_header_key(sample, ("player", "name")) is not None
        has_team = _find_header_key(sample, ("team", "club")) is not None
        has_average = _find_header_key(
            sample,
            ("season_average", "avg", "average", "fantasy_avg", "points_per_game", "ppg"),
        ) is not None
        if not (has_name and has_team and has_average):
            continue

        for row in rows:
            name_key = _find_header_key(row, ("player", "name"))
            team_key = _find_header_key(row, ("team", "club"))
            avg_key = _find_header_key(
                row,
                ("season_average", "avg", "average", "fantasy_avg", "points_per_game", "ppg"),
            )
            if not name_key or not team_key or not avg_key:
                continue

            name = row[name_key].strip()
            team = row[team_key].strip()
            if not name or not team:
                continue

            positions_raw = row.get("positions") or row.get("position") or row.get("pos") or "MID"
            positions = [value.strip() for value in re.split(r"[,/]", positions_raw) if value.strip()] or ["MID"]
            season_average = float(_parse_number(row.get(avg_key), target_type=float, default=0.0))
            last_3_average = float(
                _parse_number(
                    row.get("last_3_average") or row.get("last_3") or row.get("last3"),
                    target_type=float,
                    default=season_average,
                )
            )
            minutes_adjusted_base = float(
                _parse_number(
                    row.get("minutes_adjusted_base") or row.get("minutes") or row.get("avg_minutes"),
                    target_type=float,
                    default=season_average,
                )
            )
            price = int(_parse_number(row.get("price") or row.get("salary"), target_type=int, default=0))
            breakeven_raw = row.get("breakeven") or row.get("be")
            breakeven: int | None = None
            if breakeven_raw:
                breakeven = int(_parse_number(breakeven_raw, target_type=int, default=0))

            bye_rounds_raw = row.get("bye_rounds") or row.get("bye") or ""
            bye_rounds = [
                int(_parse_number(value, target_type=int, default=0))
                for value in re.split(r"[,/ ]+", bye_rounds_raw.strip())
                if value.strip() and int(_parse_number(value, target_type=int, default=0)) > 0
            ]

            players.append(
                Player(
                    id=row.get("id") or row.get("player_id") or _player_id(name, team),
                    name=name,
                    team=team,
                    positions=positions,
                    price=price,
                    season_average=season_average,
                    last_3_average=last_3_average,
                    minutes_adjusted_base=minutes_adjusted_base,
                    opponent_modifier=float(
                        _parse_number(row.get("opponent_modifier"), target_type=float, default=0.0)
                    ),
                    role_change_modifier=float(
                        _parse_number(row.get("role_change_modifier"), target_type=float, default=0.0)
                    ),
                    role_risk=float(_parse_number(row.get("role_risk"), target_type=float, default=0.1)),
                    injury_risk=float(_parse_number(row.get("injury_risk"), target_type=float, default=0.1)),
                    job_security_risk=float(
                        _parse_number(row.get("job_security_risk"), target_type=float, default=0.05)
                    ),
                    breakeven=breakeven,
                    bye_rounds=bye_rounds,
                    status=row.get("status") or "available",
                )
            )
        if players:
            return players

    raise RuntimeError(f"No player stats table found at {url}")


def scrape_team_game_stats(url: str) -> list[TeamGameStat]:
    html = _fetch_html(url)
    tables = _tables_as_rows(html)
    team_game_stats: list[TeamGameStat] = []
    for rows in tables:
        if not rows:
            continue
        sample = rows[0]
        has_round = _find_header_key(sample, ("round", "rnd")) is not None
        has_team = _find_header_key(sample, ("team", "club")) is not None
        has_opponent = _find_header_key(sample, ("opponent", "opp", "vs")) is not None
        has_for = _find_header_key(sample, ("points_for", "for", "pts_for", "team_score")) is not None
        has_against = _find_header_key(
            sample, ("points_against", "against", "pts_against", "opp_score")
        ) is not None
        if not (has_round and has_team and has_opponent and has_for and has_against):
            continue

        for row in rows:
            round_key = _find_header_key(row, ("round", "rnd"))
            team_key = _find_header_key(row, ("team", "club"))
            opponent_key = _find_header_key(row, ("opponent", "opp", "vs"))
            points_for_key = _find_header_key(row, ("points_for", "for", "pts_for", "team_score"))
            points_against_key = _find_header_key(
                row, ("points_against", "against", "pts_against", "opp_score")
            )
            if not all((round_key, team_key, opponent_key, points_for_key, points_against_key)):
                continue

            round_number = int(_parse_number(row.get(round_key), target_type=int, default=0))
            team = (row.get(team_key) or "").strip()
            opponent = (row.get(opponent_key) or "").strip()
            points_for = int(_parse_number(row.get(points_for_key), target_type=int, default=0))
            points_against = int(_parse_number(row.get(points_against_key), target_type=int, default=0))
            if round_number < 1 or not team or not opponent:
                continue

            result = row.get("result")
            if not result:
                if points_for > points_against:
                    result = "W"
                elif points_for < points_against:
                    result = "L"
                else:
                    result = "D"
            else:
                result = result.strip().upper()[:1]

            team_game_stats.append(
                TeamGameStat(
                    round=round_number,
                    team=team,
                    opponent=opponent,
                    points_for=points_for,
                    points_against=points_against,
                    result=result if result in {"W", "L", "D"} else None,
                )
            )
        if team_game_stats:
            return team_game_stats

    raise RuntimeError(f"No team game stats table found at {url}")
