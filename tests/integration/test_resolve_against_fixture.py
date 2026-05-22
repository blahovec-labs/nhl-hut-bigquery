# tests/integration/test_resolve_against_fixture.py
from unittest.mock import MagicMock

import pandas as pd

from nhl_hut_bigquery.xref.resolver import build_nhl_player_dim, resolve_all


def test_build_nhl_player_dim_from_synthetic_boxscore():
    client = MagicMock()
    rows = [
        MagicMock(player_id=1, full_name_normalized="JOHN DOE",
                  position_code="C", team_abbrevs=["TOR"]),
        MagicMock(player_id=2, full_name_normalized="JANE DOE",
                  position_code="L", team_abbrevs=["MTL", "TOR"]),
    ]
    client.query.return_value.result.return_value = rows

    dim = build_nhl_player_dim(client=client, nhl_boxscore_table="p.d.bs",
                                season=2024)
    assert isinstance(dim, pd.DataFrame)
    assert len(dim) == 2
    assert set(dim.columns) == {"player_id", "full_name_normalized",
                                "position_code", "team_abbrevs"}


def test_resolve_all_produces_xref_rows():
    hut_df = pd.DataFrame([
        {"card_id": "a1", "player_full_name_normalized": "JOHN DOE",
         "team_abbrev": "TOR", "position": "C", "nhl_player_id": None},
        {"card_id": "a2", "player_full_name_normalized": "MISSING",
         "team_abbrev": "BOS", "position": "C", "nhl_player_id": None},
    ])
    nhl_dim = pd.DataFrame([
        {"player_id": 1, "full_name_normalized": "JOHN DOE",
         "position_code": "C", "team_abbrevs": ["TOR"]},
    ])
    out = resolve_all(hut_df=hut_df, nhl_dim=nhl_dim,
                     snapshot_date="2026-05-22", season=2024)
    assert len(out) == 2
    by_card = {r["hut_card_id"]: r for r in out.to_dict("records")}
    assert by_card["a1"]["match_method"] == "exact_name_team_season"
    assert by_card["a1"]["resolved_nhl_player_id"] == 1
    assert by_card["a2"]["match_method"] == "unmatched"
    assert by_card["a2"]["resolved_nhl_player_id"] is None
