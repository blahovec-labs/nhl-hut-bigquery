"""Tests for CLI scaffold + sync command (HUT-T8)."""

from unittest.mock import patch

from nhl_hut_bigquery.cli import build_parser, main


def test_parser_sync():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--table", "p.d.hut", "--dry-run",
    ])
    assert ns.command == "sync"
    assert ns.table == "p.d.hut"
    assert ns.dry_run is True


def test_dry_run_no_scrape():
    with patch("nhl_hut_bigquery.cli.HUTScraper") as mock_scraper:
        ret = main(["sync", "--table", "p.d.hut", "--dry-run"])
        assert ret == 0
        mock_scraper.return_value.iter_all_cards.assert_not_called()
