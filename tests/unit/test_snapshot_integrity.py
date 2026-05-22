from unittest.mock import MagicMock

from nhl_hut_bigquery.verify.snapshot_integrity import (
    run_cross_snapshot_drift,
    run_snapshot_integrity,
)


def test_snapshot_integrity_returns_pass_on_clean_data():
    client = MagicMock()
    row = MagicMock()
    row.violations = 0
    row.total = 100
    client.query.return_value.result.return_value = [row]
    result = run_snapshot_integrity(client=client, table="p.d.hut")
    assert result.overall_pass


def test_snapshot_integrity_fails_on_violations():
    client = MagicMock()
    bad = MagicMock()
    bad.violations = 5
    bad.total = 100
    good = MagicMock()
    good.violations = 0
    good.total = 100
    rows_iter = iter([bad, good, good])
    client.query.return_value.result.side_effect = lambda: [next(rows_iter)]
    result = run_snapshot_integrity(client=client, table="p.d.hut")
    assert not result.overall_pass


def test_cross_snapshot_drift_returns_check_result():
    client = MagicMock()
    row = MagicMock()
    row.violations = 0
    row.total = 50
    client.query.return_value.result.return_value = [row]
    result = run_cross_snapshot_drift(client=client, table="p.d.hut")
    assert len(result.checks) >= 1
