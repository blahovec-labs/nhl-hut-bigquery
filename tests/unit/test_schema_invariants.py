import pytest

from nhl_hut_bigquery.schema import BqMode, BqType, ColumnSpec, PartitioningSpec


def test_columnspec_validates_required_business_definition():
    with pytest.raises(ValueError, match="business_definition required"):
        ColumnSpec(
            name="x", type="INT64", mode="NULLABLE",
            short_description="x", business_definition="",
            semantic_tags=[], valid_range=None, valid_values=None,
            example_value=None, gotchas=[],
            nhlhutbuilder_field_equivalent=None,
            nhlhutbuilder_source_field="x",
            deprecated_in_year=None,
        )


def test_columnspec_rejects_unknown_type():
    with pytest.raises(ValueError, match="invalid type"):
        ColumnSpec(
            name="x", type="GUNK", mode="NULLABLE",  # type: ignore[arg-type]
            short_description="x", business_definition="x",
            semantic_tags=[], valid_range=None, valid_values=None,
            example_value=None, gotchas=[],
            nhlhutbuilder_field_equivalent=None,
            nhlhutbuilder_source_field="x",
            deprecated_in_year=None,
        )


def test_partitioning_spec():
    p = PartitioningSpec(field="snapshot_date", type="DAY",
                         clustering=["position", "overall"])
    assert p.field == "snapshot_date"
