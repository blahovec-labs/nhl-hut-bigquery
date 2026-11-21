"""write_snapshot must never leave a snapshot deleted but not replaced.

It ran `DELETE ... WHERE snapshot_date = @d` as its own query and then a separate
load job. A BigQuery load job can't join a transaction, so a failed load left that
day's snapshot (cards or xref) gone. Same failure that wiped 2026-06-02 from
statcast-bigquery; this library's own 0.1.1 notes record a load-time type crash.

Contract now: load into a short-lived staging table FIRST, then DELETE + INSERT ...
SELECT in ONE multi-statement transaction, then drop the staging table.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from google.cloud import bigquery

from nhl_hut_bigquery.writer import BigQueryWriter, TableRef

TARGET = "p.d.hut_cards"
REF = TableRef.parse(TARGET)
SCHEMA = [
    bigquery.SchemaField("snapshot_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("card_id", "STRING"),
]


def _client() -> MagicMock:
    c = MagicMock(spec=bigquery.Client)
    c.project = "p"
    c.get_table.return_value = bigquery.Table(TARGET, schema=SCHEMA)
    return c


def _write(c: MagicMock, df: pd.DataFrame | None = None) -> int:
    if df is None:
        df = pd.DataFrame([{"snapshot_date": "2026-11-21", "card_id": "x1"},
                           {"snapshot_date": "2026-11-21", "card_id": "x2"}])
    return BigQueryWriter(client=c).write_snapshot(REF, df, snapshot_date="2026-11-21")


def _sql(c: MagicMock) -> list[str]:
    return [call.args[0] for call in c.query_and_wait.call_args_list] + [
        call.args[0] for call in c.query.call_args_list
    ]


def test_failed_load_deletes_nothing():
    c = _client()
    c.load_table_from_dataframe.return_value.result.side_effect = RuntimeError("400 load failed")
    with pytest.raises(RuntimeError):
        _write(c)
    assert not any("DELETE" in sql for sql in _sql(c))


def test_load_targets_staging_not_the_live_table():
    c = _client()
    _write(c)
    destination = str(c.load_table_from_dataframe.call_args.args[1])
    assert destination != TARGET
    assert "_staging_" in destination


def test_delete_and_insert_commit_in_one_transaction():
    c = _client()
    assert _write(c) == 2
    swaps = [sql for sql in _sql(c) if "DELETE" in sql]
    assert len(swaps) == 1
    sql = swaps[0]
    assert sql.lstrip().startswith("BEGIN TRANSACTION")
    assert sql.rstrip().endswith("COMMIT TRANSACTION;")
    assert f"DELETE FROM `{TARGET}` WHERE snapshot_date = @d" in sql
    assert sql.index("DELETE") < sql.index("INSERT INTO")
    staging = str(c.load_table_from_dataframe.call_args.args[1])
    assert f"FROM `{staging}`" in sql
    job_config = c.query_and_wait.call_args.kwargs["job_config"]
    assert [(p.name, str(p.value)) for p in job_config.query_parameters] == [("d", "2026-11-21")]


def test_staging_table_dropped_even_when_swap_fails():
    c = _client()
    c.query_and_wait.side_effect = RuntimeError("transaction aborted")
    with pytest.raises(RuntimeError):
        _write(c)
    staging = str(c.load_table_from_dataframe.call_args.args[1])
    assert staging in [str(call.args[0]) for call in c.delete_table.call_args_list]
