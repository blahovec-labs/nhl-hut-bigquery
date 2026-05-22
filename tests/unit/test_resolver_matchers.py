import pandas as pd

from nhl_hut_bigquery.xref.matchers import (
    match_exact_name_position_season,
    match_exact_name_season,
    match_exact_name_team_season,
    match_nhl_id_direct,
)


def _dim_row(player_id, name_norm, position, teams):
    return {
        "player_id": player_id,
        "full_name_normalized": name_norm,
        "position_code": position,
        "team_abbrevs": teams,
    }


def test_nhl_id_direct_present():
    hut = {"nhl_player_id": 8479318}
    nhl_dim = pd.DataFrame([_dim_row(8479318, "X", "C", ["TOR"])])
    pid, conf = match_nhl_id_direct(hut, nhl_dim)
    assert pid == 8479318
    assert conf == 1.0


def test_nhl_id_direct_absent_returns_none():
    hut = {"nhl_player_id": None}
    nhl_dim = pd.DataFrame()
    pid, conf = match_nhl_id_direct(hut, nhl_dim)
    assert pid is None and conf == 0.0


def test_name_team_season_single_match():
    hut = {"player_full_name_normalized": "AUSTON MATTHEWS", "team_abbrev": "TOR"}
    nhl_dim = pd.DataFrame([
        _dim_row(8479318, "AUSTON MATTHEWS", "C", ["TOR"]),
        _dim_row(8479319, "OTHER NAME", "L", ["MTL"]),
    ])
    pid, conf = match_exact_name_team_season(hut, nhl_dim)
    assert pid == 8479318
    assert conf == 0.95


def test_name_team_season_collision_returns_none():
    # Two AUSTON MATTHEWS on team TOR somehow → collision, fall through
    hut = {"player_full_name_normalized": "AUSTON MATTHEWS", "team_abbrev": "TOR"}
    nhl_dim = pd.DataFrame([
        _dim_row(1, "AUSTON MATTHEWS", "C", ["TOR"]),
        _dim_row(2, "AUSTON MATTHEWS", "C", ["TOR"]),
    ])
    pid, conf = match_exact_name_team_season(hut, nhl_dim)
    assert pid is None and conf == 0.0


def test_name_position_season_handles_trade():
    # Player was traded; current HUT team is BOS but their boxscore shows TOR
    hut = {"player_full_name_normalized": "TRADED PLAYER", "team_abbrev": "BOS", "position": "D"}
    nhl_dim = pd.DataFrame([
        _dim_row(5, "TRADED PLAYER", "D", ["TOR"]),
        _dim_row(6, "OTHER NAME", "C", ["BOS"]),
    ])
    pid, conf = match_exact_name_position_season(hut, nhl_dim)
    assert pid == 5
    assert conf == 0.85


def test_name_season_unique_match():
    hut = {"player_full_name_normalized": "UNIQUE NAME"}
    nhl_dim = pd.DataFrame([
        _dim_row(7, "UNIQUE NAME", "C", ["TOR"]),
    ])
    pid, conf = match_exact_name_season(hut, nhl_dim)
    assert pid == 7
    assert conf == 0.70


def test_name_season_collision_returns_none():
    hut = {"player_full_name_normalized": "COMMON NAME"}
    nhl_dim = pd.DataFrame([
        _dim_row(7, "COMMON NAME", "C", ["TOR"]),
        _dim_row(8, "COMMON NAME", "L", ["MTL"]),
    ])
    pid, conf = match_exact_name_season(hut, nhl_dim)
    assert pid is None and conf == 0.0
