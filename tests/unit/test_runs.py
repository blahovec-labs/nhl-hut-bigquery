"""Regression test for the RunsTable schemaless-table bug."""

from unittest.mock import MagicMock

from nhl_hut_bigquery.runs import RunsTable, RunsTableRef


def test_runs_table_created_with_schema():
    """SCHEMA was a dataclass field default (None) that shadowed the class attr,
    so create_table built a SCHEMALESS table and every run-log insert 400'd with
    'destination table has no schema'. It must now carry the 8-field schema."""
    client = MagicMock()
    client.get_table.side_effect = Exception("not found")  # force creation path

    rt = RunsTable(client=client)
    assert rt.SCHEMA is not None
    assert len(rt.SCHEMA) == 8

    rt.create_table_if_missing(RunsTableRef.parse("p.d._runs"))
    created_table = client.create_table.call_args[0][0]
    assert len(created_table.schema) == 8
    assert created_table.schema[0].name == "snapshot_date"
