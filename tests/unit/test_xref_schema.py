# tests/unit/test_xref_schema.py
from nhl_hut_bigquery.xref.schema import XREF_SCHEMA, get_partitioning


def test_partitioning():
    p = get_partitioning()
    assert p.field == "snapshot_date"
    assert "resolved_nhl_player_id" in p.clustering


def test_required_columns_present():
    names = {c.name for c in XREF_SCHEMA}
    expected = {"snapshot_date", "hut_card_id",
                "hut_player_full_name_normalized",
                "resolved_nhl_player_id", "match_method",
                "match_confidence", "season", "resolved_at"}
    assert expected.issubset(names), f"missing: {expected - names}"


def test_match_method_valid_values():
    spec = next(c for c in XREF_SCHEMA if c.name == "match_method")
    expected = {"nhl_id_direct", "exact_name_team_season",
                "exact_name_position_season", "exact_name_season",
                "unmatched"}
    assert set(spec.valid_values or []) >= expected
