"""ColumnSpec for HUT ratings schema — same dataclass as nhl-bigquery
with field renames for the HUT source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SCHEMA_VERSION = "0.1.0"

BqType = Literal[
    "INT64", "FLOAT64", "STRING", "BOOL", "DATE", "TIMESTAMP", "TIME", "NUMERIC",
]
BqMode = Literal["REQUIRED", "NULLABLE", "REPEATED"]

_VALID_TYPES = set(BqType.__args__)  # type: ignore[attr-defined]
_VALID_MODES = set(BqMode.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    type: BqType
    mode: BqMode
    short_description: str
    business_definition: str
    semantic_tags: list[str]
    valid_range: tuple[float, float] | None
    valid_values: list[str] | None
    example_value: object | None
    gotchas: list[str]
    nhlhutbuilder_field_equivalent: str | None
    nhlhutbuilder_source_field: str
    deprecated_in_year: int | None

    def __post_init__(self) -> None:
        if self.type not in _VALID_TYPES:
            raise ValueError(f"{self.name}: invalid type {self.type!r}")
        if self.mode not in _VALID_MODES:
            raise ValueError(f"{self.name}: invalid mode {self.mode!r}")
        if not self.business_definition.strip():
            raise ValueError(f"{self.name}: business_definition required")


@dataclass(frozen=True)
class PartitioningSpec:
    field: str
    type: Literal["DAY", "MONTH", "YEAR"]
    clustering: list[str]


def _col(name, type, mode, short, defn, *, tags=None, range_=None, values=None,
         example=None, gotchas=None, src=None, eq=None, dep=None):
    """Helper to compactly construct ColumnSpec instances."""
    return ColumnSpec(
        name=name, type=type, mode=mode,
        short_description=short, business_definition=defn,
        semantic_tags=list(tags or []),
        valid_range=range_, valid_values=values, example_value=example,
        gotchas=list(gotchas or []),
        nhlhutbuilder_field_equivalent=eq,
        nhlhutbuilder_source_field=src or name,
        deprecated_in_year=dep,
    )
