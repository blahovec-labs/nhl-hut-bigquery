# tests/unit/test_writer_idempotency.py
from unittest.mock import MagicMock

import pandas as pd
import pytest

from nhl_hut_bigquery.writer import BigQueryWriter, TableRef


def test_tableref_parse():
    ref = TableRef.parse("p.d.t")
    assert (ref.project, ref.dataset, ref.table) == ("p", "d", "t")


def test_write_snapshot_replaces_for_snapshot_date():
    client = MagicMock()
    writer = BigQueryWriter(client=client)
    ref = TableRef("p", "d", "hut")
    df = pd.DataFrame([{"snapshot_date": "2026-05-22", "card_id": "x1"}])
    writer.write_snapshot(ref, df, snapshot_date="2026-05-22")
    assert client.query.called  # DELETE issued
    assert client.load_table_from_dataframe.called  # INSERT


def test_write_snapshot_skips_empty_df():
    client = MagicMock()
    writer = BigQueryWriter(client=client)
    ref = TableRef("p", "d", "hut")
    n = writer.write_snapshot(ref, pd.DataFrame(), snapshot_date="2026-05-22")
    assert n == 0
    client.load_table_from_dataframe.assert_not_called()
