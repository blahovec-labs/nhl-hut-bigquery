"""5 doc renderers — same shape as nhl-bigquery.docs.renderers, adapted for HUT."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from google.cloud import bigquery

from nhl_hut_bigquery.docs.taxonomy import TABLES
from nhl_hut_bigquery.schema import ColumnSpec


def _doc(spec: ColumnSpec) -> str:
    parts = [spec.business_definition]
    if spec.valid_values:
        parts.append(f"Valid values: {', '.join(spec.valid_values)}.")
    if spec.valid_range is not None:
        parts.append(f"Valid range: {spec.valid_range[0]} – {spec.valid_range[1]}.")
    if spec.example_value is not None:
        parts.append(f"Example: {spec.example_value!r}.")
    if spec.gotchas:
        parts.append(
            "Gotchas: " + " ".join(f"({i + 1}) {g}" for i, g in enumerate(spec.gotchas))
        )
    if spec.nhlhutbuilder_field_equivalent:
        parts.append(f"HUT source: {spec.nhlhutbuilder_field_equivalent}.")
    if spec.deprecated_in_year is not None:
        parts.append(f"Universally NULL from {spec.deprecated_in_year} onward.")
    return " ".join(parts)


def render_bq_descriptions(table_kind: str) -> list[bigquery.SchemaField]:
    out = []
    for spec in TABLES[table_kind]["schema"]:
        out.append(
            bigquery.SchemaField(
                name=spec.name,
                field_type=spec.type,
                mode=spec.mode,
                description=_doc(spec)[:1024],
            )
        )
    return out


def render_llm_context() -> str:
    lines = ["# nhl-hut-bigquery — LLM context\n"]
    for tbl, meta in TABLES.items():
        lines.append(f"\n## Table `{tbl}`\n")
        p = meta["partitioning"]
        lines.append(
            f"Partitioned by `{p.field}` ({p.type}); clustered by {', '.join(p.clustering)}.\n"
        )
        for spec in meta["schema"]:
            lines.append(f"### `{spec.name}` ({spec.type} {spec.mode})\n")
            lines.append(_doc(spec) + "\n")
    return "\n".join(lines)


def render_markdown() -> str:
    lines = ["# nhl-hut-bigquery — Column Reference\n"]
    for tbl, meta in TABLES.items():
        lines.append(f"\n## `{tbl}`\n")
        lines.append("| Column | Type | Mode | Description |")
        lines.append("|---|---|---|---|")
        for spec in meta["schema"]:
            short = spec.short_description.replace("|", "\\|")
            lines.append(f"| `{spec.name}` | {spec.type} | {spec.mode} | {short} |")
    return "\n".join(lines)


def render_data_dictionary(*, dataset: str, table: str) -> list[dict[str, Any]]:
    now = datetime.now(UTC).isoformat()
    return [
        {
            "dataset": dataset,
            "table": table,
            "column": spec.name,
            "dtype": spec.type,
            "description": spec.short_description,
            "business_definition": _doc(spec),
            "owner": "nhl-hut-bigquery",
            "tags": list(spec.semantic_tags),
            "source_system": "nhlhutbuilder.com",
            "upstream_lineage_json": json.dumps(
                {
                    "nhlhutbuilder_field_equivalent": spec.nhlhutbuilder_field_equivalent,
                    "nhlhutbuilder_source_field": spec.nhlhutbuilder_source_field,
                }
            ),
            "created_at": now,
            "updated_at": now,
        }
        for spec in TABLES[table]["schema"]
    ]


def render_dbt_yaml() -> str:
    lines = ["version: 2", "", "models:"]
    for tbl, meta in TABLES.items():
        lines.append(f"  - name: {tbl}")
        lines.append(f'    description: "nhl-hut-bigquery {tbl} table"')
        lines.append("    columns:")
        for spec in meta["schema"]:
            short = spec.short_description.replace('"', "'")
            lines.append(f"      - name: {spec.name}")
            lines.append(f'        description: "{short}"')
    return "\n".join(lines) + "\n"


def apply_data_dictionary(
    *,
    client: Any,
    dictionary_table: str,
    dataset: str,
    table: str,
) -> int:
    """Write data dictionary rows into a BigQuery table. Returns number of rows inserted."""
    rows = render_data_dictionary(dataset=dataset, table=table)
    errors = client.insert_rows_json(dictionary_table, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")
    return len(rows)
