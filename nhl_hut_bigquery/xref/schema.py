from __future__ import annotations

from nhl_hut_bigquery.schema import ColumnSpec, PartitioningSpec, _col


def get_partitioning() -> PartitioningSpec:
    return PartitioningSpec(
        field="snapshot_date", type="DAY",
        clustering=["resolved_nhl_player_id", "match_confidence"],
    )


XREF_SCHEMA: list[ColumnSpec] = [
    _col("snapshot_date", "DATE", "REQUIRED",
         "HUT snapshot date.", "FK to hut_player_ratings.snapshot_date.",
         tags=["temporal", "identifier"], example="2026-05-22",
         eq=None, src="(input)"),
    _col("hut_card_id", "STRING", "REQUIRED",
         "HUT card identifier.", "FK to hut_player_ratings.card_id.",
         tags=["identifier", "join_key"], example="abc123",
         eq=None, src="(input)"),
    _col("hut_player_full_name_normalized", "STRING", "REQUIRED",
         "Normalized HUT player name.",
         "Match input — UPPER-cased, accent-folded, punctuation-stripped name.",
         tags=["identifier"], example="AUSTON MATTHEWS",
         eq=None, src="(input)"),
    _col("hut_team_abbrev", "STRING", "NULLABLE",
         "HUT team abbrev.", "Match input from the HUT card.",
         tags=["team"], example="TOR", eq=None, src="(input)"),
    _col("hut_position", "STRING", "NULLABLE",
         "HUT position.", "Match input.",
         tags=["identifier"], example="C", eq=None, src="(input)"),
    _col("resolved_nhl_player_id", "INT64", "NULLABLE",
         "Matched NHL player_id.",
         "NULL when match_method = 'unmatched'.",
         tags=["identifier", "join_key"], example=8479318,
         eq=None, src="(resolved)"),
    _col("match_method", "STRING", "REQUIRED",
         "How the match was made.",
         "Walked ladder result. See match_confidence for relative trust.",
         tags=["meta", "derived"],
         values=["nhl_id_direct", "exact_name_team_season",
                 "exact_name_position_season", "exact_name_season",
                 "unmatched"],
         example="exact_name_team_season",
         eq=None, src="(resolved)"),
    _col("match_confidence", "FLOAT64", "REQUIRED",
         "Match confidence (0.00-1.00).",
         "1.00 = direct NHL ID; 0.95 = name+team+season; 0.85 = name+position+season; "
         "0.70 = name+season; 0.00 = unmatched.",
         tags=["meta", "derived"], range_=(0.0, 1.0), example=0.95,
         eq=None, src="(resolved)"),
    _col("season", "INT64", "REQUIRED",
         "Season used for the match.",
         "NHL season start year (e.g. 2024 for 2024-25). Match attempts are "
         "season-scoped against the NHL player dim derived from that season's boxscore_stats.",
         tags=["temporal"], range_=(2010.0, 2050.0), example=2024,
         eq=None, src="(input)"),
    _col("resolved_at", "TIMESTAMP", "REQUIRED",
         "Resolution timestamp.",
         "UTC timestamp when the resolver wrote this row.",
         tags=["meta"], example="2026-05-22T17:00:00Z",
         eq=None, src="(set by resolver)"),
]
