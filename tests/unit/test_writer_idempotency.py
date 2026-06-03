# tests/unit/test_writer_idempotency.py
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest
from google.cloud import bigquery

from nhl_hut_bigquery.writer import BigQueryWriter, TableRef, _coerce_df_for_bq


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


def test_coerce_df_casts_string_date_nullable_int_and_timestamp():
    """Regression: snapshot_date arrived as strings -> pyarrow could not load it
    into a DATE column. Coercion must produce date objects, nullable Int64, and
    tz-aware timestamps; STRING columns pass through unchanged."""
    schema = [
        bigquery.SchemaField("snapshot_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("overall", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("player_full_name", "STRING", mode="NULLABLE"),
    ]
    df = pd.DataFrame([
        {"snapshot_date": "2026-06-02", "overall": 84,
         "ingested_at": datetime(2026, 6, 2, tzinfo=timezone.utc),
         "player_full_name": "TROY TERRY"},
        {"snapshot_date": "2026-06-02", "overall": None,
         "ingested_at": datetime(2026, 6, 2, tzinfo=timezone.utc),
         "player_full_name": None},
    ])
    out = _coerce_df_for_bq(df, schema)
    assert out["snapshot_date"].iloc[0] == date(2026, 6, 2)
    assert str(out["overall"].dtype) == "Int64"
    assert out["overall"].iloc[0] == 84
    assert pd.isna(out["overall"].iloc[1])
    assert str(out["ingested_at"].dtype).startswith("datetime64[ns, UTC")
    assert out["player_full_name"].iloc[0] == "TROY TERRY"
