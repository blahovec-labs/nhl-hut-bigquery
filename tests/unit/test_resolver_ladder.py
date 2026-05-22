import pandas as pd

from nhl_hut_bigquery.xref.matchers import resolve_card


def _dim_row(player_id, name_norm, position, teams):
    return {
        "player_id": player_id,
        "full_name_normalized": name_norm,
        "position_code": position,
        "team_abbrevs": teams,
    }


def test_ladder_prefers_nhl_id_direct():
    hut = {
        "nhl_player_id": 99,
        "player_full_name_normalized": "FOO",
        "team_abbrev": "TOR",
        "position": "C",
    }
    nhl_dim = pd.DataFrame([_dim_row(99, "FOO", "C", ["TOR"])])
    pid, method, conf = resolve_card(hut, nhl_dim)
    assert pid == 99
    assert method == "nhl_id_direct"
    assert conf == 1.0


def test_ladder_falls_to_name_team_when_no_direct_id():
    hut = {
        "nhl_player_id": None,
        "player_full_name_normalized": "JOHN DOE",
        "team_abbrev": "TOR",
        "position": "C",
    }
    nhl_dim = pd.DataFrame([_dim_row(5, "JOHN DOE", "C", ["TOR"])])
    pid, method, conf = resolve_card(hut, nhl_dim)
    assert pid == 5
    assert method == "exact_name_team_season"


def test_ladder_returns_unmatched_when_no_method_succeeds():
    hut = {
        "nhl_player_id": None,
        "player_full_name_normalized": "MISSING PLAYER",
        "team_abbrev": "TOR",
        "position": "C",
    }
    nhl_dim = pd.DataFrame()
    pid, method, conf = resolve_card(hut, nhl_dim)
    assert pid is None
    assert method == "unmatched"
    assert conf == 0.0


def test_ladder_handles_collision_by_falling_through():
    # Two TOR Cs with the same name → name_team collides → falls to name_position
    # → that ALSO collides (two Cs) → falls to name_season → also collides → unmatched
    hut = {
        "nhl_player_id": None,
        "player_full_name_normalized": "COLLIDED",
        "team_abbrev": "TOR",
        "position": "C",
    }
    nhl_dim = pd.DataFrame([
        _dim_row(1, "COLLIDED", "C", ["TOR"]),
        _dim_row(2, "COLLIDED", "C", ["TOR"]),
    ])
    pid, method, conf = resolve_card(hut, nhl_dim)
    assert method == "unmatched"
    assert pid is None
