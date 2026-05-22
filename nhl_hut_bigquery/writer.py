"""BigQueryWriter + TableRef for snapshot-typed HUT data."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
from google.cloud import bigquery

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TableRef:
    project: str
    dataset: str
    table: str

    def __str__(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}"

    @classmethod
    def parse(cls, s: str) -> "TableRef":
        parts = s.split(".")
        if len(parts) != 3:
            raise ValueError(f"expected project.dataset.table, got {s!r}")
        return cls(*parts)


class BigQueryWriter:
    def __init__(self, client: bigquery.Client | None = None) -> None:
        self.client = client or bigquery.Client()

    def create_table_if_missing(
        self,
        ref: TableRef,
        schema: list[bigquery.SchemaField],
        partition_field: str = "snapshot_date",
        clustering: list[str] | None = None,
    ) -> None:
        try:
            self.client.get_table(str(ref))
        except Exception:
            t = bigquery.Table(str(ref), schema=schema)
            t.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY, field=partition_field
            )
            if clustering:
                t.clustering_fields = clustering
            self.client.create_table(t)
            log.info("created table %s", ref)

    def write_snapshot(
        self,
        ref: TableRef,
        df: pd.DataFrame,
        *,
        snapshot_date: str,
    ) -> int:
        """Delete existing rows for snapshot_date, then insert df. Returns row count.

        Uses a parameterized DATE binding — not string interpolation — for the DELETE.
        Returns 0 and skips the load call when df is empty.
        """
        if df.empty:
            log.info("write_snapshot: empty df, skipping")
            return 0

        delete_sql = f"DELETE FROM `{ref}` WHERE snapshot_date = @d"
        self.client.query(
            delete_sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("d", "DATE", snapshot_date),
                ],
            ),
        ).result()

        load = self.client.load_table_from_dataframe(
            df,
            str(ref),
            job_config=bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            ),
        )
        load.result()
        log.info(
            "inserted %d rows into %s for snapshot %s", len(df), ref, snapshot_date
        )
        return len(df)
