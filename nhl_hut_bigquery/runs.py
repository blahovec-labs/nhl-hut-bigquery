"""RunsTable: one row per snapshot sync attempt."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar

from google.cloud import bigquery

from nhl_hut_bigquery.writer import TableRef

log = logging.getLogger(__name__)


class RunsTableRef(TableRef):
    """Typed subclass of TableRef marking the runs log table."""


@dataclass
class RunsTable:
    client: bigquery.Client

    # MUST be a ClassVar, not a dataclass field. As a field with default None,
    # __init__ set self.SCHEMA = None (shadowing the class attr that the old
    # __post_init__ populated), so create_table built a SCHEMALESS table and
    # every insert_rows_json failed with "destination table has no schema".
    SCHEMA: ClassVar[list[bigquery.SchemaField]] = [
        bigquery.SchemaField("snapshot_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("run_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("rows_written", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("cards_seen", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("endpoint_used", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("run_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    def create_table_if_missing(self, ref: RunsTableRef) -> None:
        try:
            self.client.get_table(str(ref))
            return
        except Exception:
            pass
        self.client.create_table(bigquery.Table(str(ref), schema=self.SCHEMA))
        log.info("created runs table %s", ref)

    def record(
        self,
        *,
        ref: RunsTableRef,
        snapshot_date: str,
        run_type: str,
        status: str,
        rows_written: int | None = None,
        cards_seen: int | None = None,
        endpoint_used: str | None = None,
        error: str | None = None,
    ) -> None:
        """Insert a single run-log row. Handles success, empty, and failed status values."""
        row = {
            "snapshot_date": snapshot_date,
            "run_type": run_type,
            "status": status,
            "rows_written": rows_written,
            "cards_seen": cards_seen,
            "endpoint_used": endpoint_used,
            "error": error,
            "run_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(str(ref), [row])
        if errors:
            log.warning("runs insert errors: %s", errors)
