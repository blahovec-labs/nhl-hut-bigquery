"""Resolver orchestrator: build NHL player dim → walk HUT cards → emit xref rows.

Limitation (v0.1): boxscore_stats does not carry a player_full_name column.
The SQL below emits an empty string for player_full_name, so full_name_normalized
in the returned dim is always '' (empty). The matcher ladder compensates:
  - match_nhl_id_direct does not need the name at all.
  - The three name-based matchers will not fire for players whose HUT normalized
    name cannot be paired with a non-empty dim name.

In practice this means only the direct-ID matcher is effective from the dim alone.
Name-based matching requires the caller to pre-populate full_name_normalized via
a separate player metadata source (e.g., NHL API /people or a manually maintained
lookup table), or an enriched dim built outside of this function.

The function signature is stable; callers may replace the BQ SQL or pass in a
pre-built dim DataFrame via a higher-level wrapper without changing downstream code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
from google.cloud import bigquery

from nhl_hut_bigquery.xref.matchers import resolve_card


def build_nhl_player_dim(
    *,
    client: bigquery.Client,
    nhl_boxscore_table: str,
    season: int,
) -> pd.DataFrame:
    """Materialize a season-scoped player dimension from boxscore_stats.

    Parameters
    ----------
    client:
        BigQuery client.
    nhl_boxscore_table:
        Fully-qualified ``project.dataset.table`` name for the
        ``boxscore_stats`` table from ``nhl-bigquery``.
    season:
        NHL season start year (e.g., 2024 for the 2024-25 season).

    Returns
    -------
    pd.DataFrame with columns:
        player_id (int), full_name_normalized (str), position_code (str),
        team_abbrevs (list[str])

    Notes
    -----
    The ``boxscore_stats`` table does not expose a ``player_full_name`` column.
    v0.1 workaround: ``full_name_normalized`` is set to ``''`` for all rows.
    The matchers that rely on normalized name (exact_name_team_season,
    exact_name_position_season, exact_name_season) will therefore not fire
    unless the caller enriches the returned DataFrame with real names before
    passing it to ``resolve_all``.
    """
    # Derive the games table name from the boxscore table name by replacing
    # the table component. Falls back gracefully if the convention differs.
    parts = nhl_boxscore_table.rsplit(".", 1)
    games_table = (
        f"{parts[0]}.games" if len(parts) == 2 else nhl_boxscore_table
    )

    sql = f"""
    SELECT
      player_id,
      -- boxscore_stats has no full_name column (v0.1 limitation).
      -- full_name_normalized is left blank; name-based matchers require
      -- a separate enrichment step to populate this field.
      '' AS full_name_normalized,
      ANY_VALUE(position_code) AS position_code,
      ARRAY_AGG(DISTINCT team_abbrev IGNORE NULLS) AS team_abbrevs
    FROM (
      SELECT
        bs.player_id,
        bs.position_code,
        COALESCE(g.home_team_abbrev, g.away_team_abbrev) AS team_abbrev
      FROM `{nhl_boxscore_table}` bs
      LEFT JOIN `{games_table}` g
        ON bs.game_id = g.game_id
      WHERE
        (EXTRACT(YEAR FROM bs.game_date) = {season})
        OR (
          EXTRACT(YEAR FROM bs.game_date) = {season + 1}
          AND EXTRACT(MONTH FROM bs.game_date) <= 6
        )
    )
    GROUP BY player_id
    """
    rows = list(client.query(sql).result())
    return pd.DataFrame(
        [
            {
                "player_id": int(r.player_id),
                "full_name_normalized": r.full_name_normalized,
                "position_code": r.position_code,
                "team_abbrevs": list(r.team_abbrevs) if r.team_abbrevs else [],
            }
            for r in rows
        ]
    )


def resolve_all(
    *,
    hut_df: pd.DataFrame,
    nhl_dim: pd.DataFrame,
    snapshot_date: str,
    season: int,
) -> pd.DataFrame:
    """Apply the resolver ladder to every HUT row and return an xref DataFrame.

    Parameters
    ----------
    hut_df:
        DataFrame of HUT rows for the given snapshot. Expected columns:
        card_id, player_full_name_normalized, team_abbrev, position,
        nhl_player_id.
    nhl_dim:
        Season-scoped NHL player dimension (from ``build_nhl_player_dim``).
    snapshot_date:
        ISO-format date string (YYYY-MM-DD) for the xref partition key.
    season:
        NHL season start year.

    Returns
    -------
    pd.DataFrame with the 10 columns matching XREF_SCHEMA:
        snapshot_date, hut_card_id, hut_player_full_name_normalized,
        hut_team_abbrev, hut_position, resolved_nhl_player_id,
        match_method, match_confidence, season, resolved_at.
    """
    now = datetime.now(UTC)
    out_rows: list[dict[str, Any]] = []

    for _, hut in hut_df.iterrows():
        hut_dict = hut.to_dict()
        pid, method, conf = resolve_card(hut_dict, nhl_dim)
        out_rows.append(
            {
                "snapshot_date": snapshot_date,
                "hut_card_id": hut_dict.get("card_id"),
                "hut_player_full_name_normalized": hut_dict.get(
                    "player_full_name_normalized"
                ),
                "hut_team_abbrev": hut_dict.get("team_abbrev"),
                "hut_position": hut_dict.get("position"),
                "resolved_nhl_player_id": pid,
                "match_method": method,
                "match_confidence": conf,
                "season": season,
                "resolved_at": now,
            }
        )

    df = pd.DataFrame(out_rows)
    # Preserve None (not NaN) for unmatched player_ids so callers can use
    # `is None` checks and BigQuery writer maps them to NULL correctly.
    # pandas promotes int+None columns to float64/NaN; cast to object to restore
    # Python-native None.
    if "resolved_nhl_player_id" in df.columns:
        df["resolved_nhl_player_id"] = df["resolved_nhl_player_id"].astype(object)
        df["resolved_nhl_player_id"] = df["resolved_nhl_player_id"].where(
            df["resolved_nhl_player_id"].notna(), other=None
        )
    return df
