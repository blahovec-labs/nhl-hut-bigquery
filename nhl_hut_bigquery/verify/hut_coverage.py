"""HUT coverage metric: what fraction of NHL minutes are represented by HUT cards?

Joins hut_player_xref + nhl-bigquery's boxscore_stats to compute:
  - hut_cards: count in xref for the snapshot+season
  - resolved: count where match_method != 'unmatched'
  - unmatched: count where match_method == 'unmatched'
  - distinct_resolved_players: distinct player_ids covered by HUT
  - distinct_nhl_players: distinct player_ids in boxscore for season
  - toi_seconds_total: sum of toi in boxscore for season
  - toi_seconds_covered: sum of toi for players covered by HUT

Headline metric: pct_nhl_minutes = toi_seconds_covered / toi_seconds_total
"""

from __future__ import annotations

from google.cloud import bigquery

from nhl_hut_bigquery.verify.base import CheckResult, VerifyResult


def compute_hut_coverage(
    *,
    client: bigquery.Client,
    xref_table: str,
    nhl_boxscore_table: str,
    season: int,
    snapshot_date: str,
    threshold: float = 0.90,
) -> VerifyResult:
    """Compute HUT coverage metrics for a season + snapshot.

    Returns a VerifyResult with two checks:
      - hut_coverage.pct_nhl_minutes — passes if pct_nhl_minutes >= threshold
      - hut_coverage.pct_nhl_players — passes if pct_nhl_players >= threshold
    """
    season_start = f"{season}-08-01"
    season_end = f"{season + 1}-06-30"

    sql = f"""
    WITH x AS (
      SELECT *
      FROM `{xref_table}`
      WHERE season = {season}
        AND snapshot_date = DATE '{snapshot_date}'
    ),
    bs AS (
      SELECT
        player_id,
        SUM(
          CAST(SPLIT(toi, ':')[OFFSET(0)] AS INT64) * 60
          + CAST(SPLIT(toi, ':')[OFFSET(1)] AS INT64)
        ) AS toi_seconds
      FROM `{nhl_boxscore_table}`
      WHERE game_date BETWEEN DATE '{season_start}' AND DATE '{season_end}'
        AND toi IS NOT NULL
      GROUP BY player_id
    ),
    covered AS (
      SELECT DISTINCT resolved_nhl_player_id AS player_id
      FROM x
      WHERE resolved_nhl_player_id IS NOT NULL
    )
    SELECT
      (SELECT COUNT(*) FROM x)                                          AS hut_cards,
      (SELECT COUNT(*) FROM x WHERE match_method != 'unmatched')        AS resolved,
      (SELECT COUNT(*) FROM x WHERE match_method = 'unmatched')         AS unmatched,
      (SELECT COUNT(DISTINCT player_id) FROM covered)                   AS distinct_resolved_players,
      (SELECT COUNT(DISTINCT player_id) FROM bs)                        AS distinct_nhl_players,
      (SELECT COALESCE(SUM(toi_seconds), 0) FROM bs)                    AS toi_seconds_total,
      (SELECT COALESCE(SUM(bs.toi_seconds), 0)
         FROM bs JOIN covered USING(player_id))                         AS toi_seconds_covered
    """

    row = next(iter(client.query(sql).result()))

    pct_nhl_minutes = (
        row.toi_seconds_covered / row.toi_seconds_total
        if row.toi_seconds_total
        else 0.0
    )
    pct_nhl_players = (
        row.distinct_resolved_players / row.distinct_nhl_players
        if row.distinct_nhl_players
        else 0.0
    )

    print(
        f"season={season} snapshot_date={snapshot_date} "
        f"hut_cards={row.hut_cards} resolved={row.resolved} unmatched={row.unmatched} "
        f"pct_nhl_players={pct_nhl_players:.4f} "
        f"pct_nhl_minutes={pct_nhl_minutes:.4f}"
    )

    result = VerifyResult()
    result.checks.append(
        CheckResult(
            name=f"hut_coverage.pct_nhl_minutes[season={season} snapshot={snapshot_date}]",
            violations=0 if pct_nhl_minutes >= threshold else 1,
            total=1,
            passed=pct_nhl_minutes >= threshold,
        )
    )
    result.checks.append(
        CheckResult(
            name=f"hut_coverage.pct_nhl_players[season={season} snapshot={snapshot_date}]",
            violations=0 if pct_nhl_players >= threshold else 1,
            total=1,
            passed=pct_nhl_players >= threshold,
        )
    )
    return result
