from __future__ import annotations

from google.cloud import bigquery

from nhl_hut_bigquery.verify.base import CheckResult, VerifyResult


def _q(client: bigquery.Client, sql: str) -> tuple[int, int]:
    rows = list(client.query(sql).result())
    if not rows:
        return (0, 0)
    r = rows[0]
    return (int(getattr(r, "violations", 0)), int(getattr(r, "total", 0)))


def run_snapshot_integrity(
    *,
    client: bigquery.Client,
    table: str,
    snapshot_date: str | None = None,
) -> VerifyResult:
    """Run 3 zero-tolerance snapshot integrity checks against a HUT ratings table.

    Checks:
    1. overall_in_range — overall NULL OR overall NOT BETWEEN 60 AND 99
    2. ratings_in_range — key skater/goalie rating columns outside 0-99
    3. no_dupe_rows — (snapshot_date, card_id) pairs with COUNT > 1
    """
    where = f"AND snapshot_date = DATE '{snapshot_date}'" if snapshot_date else ""
    result = VerifyResult()

    checks = [
        (
            "overall_in_range",
            f"""
            SELECT
              SUM(IF(overall IS NULL OR overall NOT BETWEEN 60 AND 99, 1, 0)) AS violations,
              COUNT(*) AS total
            FROM `{table}` WHERE 1=1 {where}
            """,
        ),
        (
            "ratings_in_range",
            f"""
            WITH ratings AS (
              SELECT speed, slap_shot_power, puck_control, def_awareness, body_checking,
                     glove_high, glove_low, stick_high, stick_low,
                     five_hole, rebound_control
              FROM `{table}` WHERE 1=1 {where}
            )
            SELECT
              SUM(IF(
                (speed IS NOT NULL AND speed NOT BETWEEN 0 AND 99)
                OR (slap_shot_power IS NOT NULL AND slap_shot_power NOT BETWEEN 0 AND 99)
                OR (puck_control IS NOT NULL AND puck_control NOT BETWEEN 0 AND 99)
                OR (def_awareness IS NOT NULL AND def_awareness NOT BETWEEN 0 AND 99)
                OR (body_checking IS NOT NULL AND body_checking NOT BETWEEN 0 AND 99)
                OR (glove_high IS NOT NULL AND glove_high NOT BETWEEN 0 AND 99)
                OR (glove_low IS NOT NULL AND glove_low NOT BETWEEN 0 AND 99)
                OR (stick_high IS NOT NULL AND stick_high NOT BETWEEN 0 AND 99)
                OR (stick_low IS NOT NULL AND stick_low NOT BETWEEN 0 AND 99)
                OR (five_hole IS NOT NULL AND five_hole NOT BETWEEN 0 AND 99)
                OR (rebound_control IS NOT NULL AND rebound_control NOT BETWEEN 0 AND 99),
              1, 0)) AS violations,
              COUNT(*) AS total
            FROM ratings
            """,
        ),
        (
            "no_dupe_rows",
            f"""
            WITH dupes AS (
              SELECT snapshot_date, card_id, COUNT(*) AS n
              FROM `{table}` WHERE 1=1 {where}
              GROUP BY snapshot_date, card_id
              HAVING COUNT(*) > 1
            )
            SELECT
              (SELECT COUNT(*) FROM dupes) AS violations,
              (SELECT COUNT(*) FROM `{table}` WHERE 1=1 {where}) AS total
            """,
        ),
    ]

    for name, sql in checks:
        v, t = _q(client, sql)
        result.checks.append(
            CheckResult(name=name, violations=v, total=t, passed=(v == 0))
        )
    return result


def run_cross_snapshot_drift(
    *,
    client: bigquery.Client,
    table: str,
    max_overall_drift: int = 5,
) -> VerifyResult:
    """Check that consecutive snapshots for the same card_id don't drift more than
    max_overall_drift points in overall rating.

    Uses LAG() over (PARTITION BY card_id ORDER BY snapshot_date).
    """
    sql = f"""
    WITH ordered AS (
      SELECT
        card_id,
        snapshot_date,
        overall,
        LAG(overall) OVER (PARTITION BY card_id ORDER BY snapshot_date) AS prev_overall
      FROM `{table}`
    )
    SELECT
      SUM(IF(
        prev_overall IS NOT NULL
        AND ABS(overall - prev_overall) > {max_overall_drift},
      1, 0)) AS violations,
      COUNT(*) AS total
    FROM ordered
    WHERE prev_overall IS NOT NULL
    """
    v, t = _q(client, sql)
    result = VerifyResult()
    result.checks.append(
        CheckResult(
            name=f"cross_snapshot_drift_<={max_overall_drift}",
            violations=v,
            total=t,
            passed=(v == 0),
        )
    )
    return result
