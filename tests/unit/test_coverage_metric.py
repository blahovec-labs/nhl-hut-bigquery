"""Tests for compute_hut_coverage — HUT-T14."""

from unittest.mock import MagicMock

from nhl_hut_bigquery.verify.hut_coverage import compute_hut_coverage


def test_compute_coverage_full():
    client = MagicMock()
    row = MagicMock()
    row.hut_cards = 100
    row.resolved = 95
    row.unmatched = 5
    row.distinct_resolved_players = 90
    row.distinct_nhl_players = 100
    row.toi_seconds_total = 1_000_000
    row.toi_seconds_covered = 950_000
    client.query.return_value.result.return_value = [row]
    result = compute_hut_coverage(
        client=client,
        xref_table="p.d.x",
        nhl_boxscore_table="p.d.bs",
        season=2024,
        snapshot_date="2026-05-22",
        threshold=0.90,
    )
    # pct_nhl_minutes = 950_000 / 1_000_000 = 0.95 >= 0.90
    assert result.checks[0].passed
    # pct_nhl_players = 90 / 100 = 0.90 >= 0.90
    assert result.checks[1].passed


def test_compute_coverage_fails_below_threshold():
    client = MagicMock()
    row = MagicMock()
    row.hut_cards = 100
    row.resolved = 50
    row.unmatched = 50
    row.distinct_resolved_players = 50
    row.distinct_nhl_players = 100
    row.toi_seconds_total = 1_000_000
    row.toi_seconds_covered = 800_000  # 80%
    client.query.return_value.result.return_value = [row]
    result = compute_hut_coverage(
        client=client,
        xref_table="p.d.x",
        nhl_boxscore_table="p.d.bs",
        season=2024,
        snapshot_date="2026-05-22",
        threshold=0.90,
    )
    # pct_nhl_minutes = 0.80 < 0.90 → FAIL
    assert not result.checks[0].passed
    # pct_nhl_players = 50 / 100 = 0.50 < 0.90 → FAIL
    assert not result.checks[1].passed
