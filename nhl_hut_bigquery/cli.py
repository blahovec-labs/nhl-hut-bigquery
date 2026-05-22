"""CLI entrypoint for nhl-hut-bigquery: {sync, docs, verify, resolve-ids}.

sync scrapes BOTH the skater and goalie endpoints by default and combines
them into a single snapshot write.  Use --skip-skaters or --skip-goalies
to limit the run to one endpoint.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date as _date
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

from nhl_hut_bigquery._version import __version__
from nhl_hut_bigquery.client import HUTScraper
from nhl_hut_bigquery.parser import check_payload_size, parse_card
from nhl_hut_bigquery.runs import RunsTable, RunsTableRef
from nhl_hut_bigquery.writer import BigQueryWriter, TableRef

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("nhl-hut-bigquery")

# Canonical endpoint URLs
_SKATER_URL = "https://nhlhutbuilder.com/NHL26/php/player_stats.php"
_GOALIE_URL = "https://nhlhutbuilder.com/NHL26/php/goalie_stats.php"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nhl-hut-bigquery")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------------
    # sync
    # ------------------------------------------------------------------
    p_sync = sub.add_parser("sync", help="Scrape HUT site and write a snapshot")
    p_sync.add_argument("--table", required=True,
                        help="Destination table: project.dataset.table")
    p_sync.add_argument("--runs-table", dest="runs_table",
                        help="Run-log table (default: <dataset>._nhl_hut_ingest_runs)")
    p_sync.add_argument("--snapshot-date", dest="snapshot_date",
                        default=_date.today().isoformat(),
                        help="Snapshot date YYYY-MM-DD (default: today)")
    skip_grp = p_sync.add_mutually_exclusive_group()
    skip_grp.add_argument("--skip-skaters", dest="skip_skaters",
                          action="store_true", default=False,
                          help="Only scrape the goalie endpoint")
    skip_grp.add_argument("--skip-goalies", dest="skip_goalies",
                          action="store_true", default=False,
                          help="Only scrape the skater endpoint")
    p_sync.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Log what would run without scraping or writing")

    # ------------------------------------------------------------------
    # docs  (stub — implemented in HUT-T9)
    # ------------------------------------------------------------------
    p_docs = sub.add_parser("docs", help="Render documentation")
    p_docs.add_argument("--format", required=True,
                        choices=["bq-apply", "llm", "dictionary", "markdown", "dbt"])
    p_docs.add_argument("--table")
    p_docs.add_argument("--dataset")
    p_docs.add_argument("--output", default="-")
    p_docs.add_argument("--apply", action="store_true")
    p_docs.add_argument("--dictionary-table")

    # ------------------------------------------------------------------
    # verify  (stub — implemented in HUT-T10 + HUT-T14)
    # ------------------------------------------------------------------
    p_v = sub.add_parser("verify", help="Verify a snapshot or cross-source coverage")
    p_v.add_argument("--aggregation", required=True,
                     choices=["snapshot-integrity", "cross-snapshot-drift", "hut-coverage"])
    p_v.add_argument("--table")
    p_v.add_argument("--xref-table")
    p_v.add_argument("--nhl-boxscore-table")
    p_v.add_argument("--season", type=int)
    p_v.add_argument("--snapshot-date")
    p_v.add_argument("--threshold", type=float, default=0.95)
    p_v.add_argument("--output", default="-")

    # ------------------------------------------------------------------
    # resolve-ids  (stub — implemented in HUT-T13)
    # ------------------------------------------------------------------
    p_r = sub.add_parser("resolve-ids",
                         help="Resolve HUT cards to NHL player_ids via match ladder")
    p_r.add_argument("--xref-table", required=True)
    p_r.add_argument("--hut-table", required=True)
    p_r.add_argument("--nhl-boxscore-table", required=True)
    p_r.add_argument("--season", type=int)
    p_r.add_argument("--snapshot-date")
    p_r.add_argument("--dry-run", action="store_true")

    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_runs_ref(table: str) -> str:
    base = TableRef.parse(table)
    return f"{base.project}.{base.dataset}._nhl_hut_ingest_runs"


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


def cmd_sync(ns: argparse.Namespace) -> int:
    ref = TableRef.parse(ns.table)
    snapshot_date: str = ns.snapshot_date
    skip_skaters: bool = ns.skip_skaters
    skip_goalies: bool = ns.skip_goalies

    endpoints: list[str] = []
    if not skip_skaters:
        endpoints.append(_SKATER_URL)
    if not skip_goalies:
        endpoints.append(_GOALIE_URL)

    if ns.dry_run:
        log.info(
            "dry-run: would sync snapshot %s into %s using endpoints: %s",
            snapshot_date,
            ref,
            ", ".join(endpoints) if endpoints else "(none)",
        )
        return 0

    bq = bigquery.Client()
    writer = BigQueryWriter(client=bq)
    runs = RunsTable(client=bq)
    runs_ref = RunsTableRef.parse(ns.runs_table or _default_runs_ref(ns.table))
    runs.create_table_if_missing(runs_ref)

    all_rows: list[dict] = []
    total_seen: int = 0
    endpoints_used: list[str] = []

    try:
        for url in endpoints:
            scraper = HUTScraper(url=url)
            for card in scraper.iter_all_cards():
                total_seen += 1
                row = parse_card(card, snapshot_date=snapshot_date, source_url=url)
                all_rows.append(row)
            endpoints_used.append(url)
            log.info("scraped %d cards so far (endpoint: %s)", total_seen, url)

        # Trip-wire: fail fast on degenerate payloads
        check_payload_size(card_count=total_seen)

        df = pd.DataFrame(all_rows)
        n = writer.write_snapshot(ref, df, snapshot_date=snapshot_date)

        runs.record(
            ref=runs_ref,
            snapshot_date=snapshot_date,
            run_type="sync",
            status="success",
            rows_written=n,
            cards_seen=total_seen,
            endpoint_used=", ".join(endpoints_used),
        )
        log.info("wrote %d rows for snapshot %s", n, snapshot_date)
        return 0

    except Exception as exc:
        runs.record(
            ref=runs_ref,
            snapshot_date=snapshot_date,
            run_type="sync",
            status="failed",
            cards_seen=total_seen,
            endpoint_used=", ".join(endpoints_used),
            error=str(exc),
        )
        raise


# ---------------------------------------------------------------------------
# Stubs (implemented in later tasks)
# ---------------------------------------------------------------------------


def cmd_docs(ns: argparse.Namespace) -> int:
    from nhl_hut_bigquery.docs.renderers import (
        render_bq_descriptions,
        render_data_dictionary,
        render_dbt_yaml,
        render_llm_context,
        render_markdown,
    )

    if ns.format == "bq-apply":
        if not ns.table:
            log.error("--table required for bq-apply")
            return 2
        ref = TableRef.parse(ns.table)
        client = bigquery.Client()
        table_obj = client.get_table(str(ref))
        table_obj.schema = render_bq_descriptions(table_kind="hut_player_ratings")
        client.update_table(table_obj, ["schema"])
        return 0

    if ns.format == "dictionary":
        if not (ns.dataset and ns.table):
            log.error("--dataset and --table required for dictionary format")
            return 2
        ref = TableRef.parse(ns.table)
        out = json.dumps(
            render_data_dictionary(dataset=ns.dataset, table=ref.table), indent=2
        )
    elif ns.format == "llm":
        out = render_llm_context()
    elif ns.format == "markdown":
        out = render_markdown()
    elif ns.format == "dbt":
        out = render_dbt_yaml()
    else:
        raise AssertionError(ns.format)

    if ns.output == "-":
        sys.stdout.write(out)
    else:
        Path(ns.output).write_text(out, encoding="utf-8")
    return 0


def cmd_verify(ns: argparse.Namespace) -> int:
    # Implemented in HUT-T10 + HUT-T14
    raise NotImplementedError("verify — Tasks 10, 14")


def cmd_resolve_ids(ns: argparse.Namespace) -> int:
    # Implemented in HUT-T13
    raise NotImplementedError("resolve-ids — Task 13")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    if ns.command == "sync":
        return cmd_sync(ns)
    if ns.command == "docs":
        return cmd_docs(ns)
    if ns.command == "verify":
        return cmd_verify(ns)
    if ns.command == "resolve-ids":
        return cmd_resolve_ids(ns)
    raise AssertionError(f"unhandled command: {ns.command!r}")


if __name__ == "__main__":
    sys.exit(main())
