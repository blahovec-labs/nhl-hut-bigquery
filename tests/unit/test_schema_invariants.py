import pytest

from nhl_hut_bigquery.schema import (
    HUT_RATINGS_SCHEMA,
    ColumnSpec,
    PartitioningSpec,
    get_partitioning,
)


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


def test_partitioning_snapshot_date():
    p = get_partitioning()
    assert p.field == "snapshot_date"
    assert "position" in p.clustering
    assert "overall" in p.clustering


def test_required_columns_present():
    names = {c.name for c in HUT_RATINGS_SCHEMA}
    required = {
        "snapshot_date", "card_id", "ingested_at",
        "player_full_name", "player_full_name_normalized",
        "position", "team_abbrev", "overall",
    }
    assert required.issubset(names), f"missing: {required - names}"


def test_overall_is_int_with_valid_range():
    spec = next(c for c in HUT_RATINGS_SCHEMA if c.name == "overall")
    assert spec.type == "INT64"
    assert spec.valid_range == (60.0, 99.0)
