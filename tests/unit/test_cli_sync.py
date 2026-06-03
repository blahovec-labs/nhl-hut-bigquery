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


def test_goalie_endpoint_tagged_in_sync():
    """cmd_sync must pass force_position='G' for the goalie endpoint so goalie
    ratings survive and ids are namespaced; the skater endpoint stays untouched."""
    skater_raw = {"card_art": '<a id="1001">TROY TERRY</a>', "full_name": "Troy Terry",
                  "position": "RW", "team": "ANA", "overall": "84"}
    goalie_raw = {"card_art": '<a id="1001">LUKAS DOSTAL</a>', "full_name": "Lukas Dostal",
                  "team": "ANA", "overall": "81", "glove_high": "85"}  # no position key

    class FakeScraper:
        def __init__(self, url):
            self.url = url

        def iter_all_cards(self):
            yield goalie_raw if "goalie" in self.url else skater_raw

    captured = {}

    def fake_write(self, ref, df, *, snapshot_date):
        captured["df"] = df
        return len(df)

    with patch("nhl_hut_bigquery.cli.HUTScraper", FakeScraper), \
         patch("nhl_hut_bigquery.cli.bigquery.Client"), \
         patch("nhl_hut_bigquery.cli.check_payload_size"), \
         patch("nhl_hut_bigquery.cli.BigQueryWriter.write_snapshot", new=fake_write), \
         patch("nhl_hut_bigquery.cli.RunsTable.create_table_if_missing"), \
         patch("nhl_hut_bigquery.cli.RunsTable.record"):
        ret = main(["sync", "--table", "p.d.hut", "--snapshot-date", "2026-06-02"])

    assert ret == 0
    df = captured["df"]
    goalie = df[df["source_url"].str.contains("goalie")].iloc[0]
    skater = df[~df["source_url"].str.contains("goalie")].iloc[0]
    assert goalie["position"] == "G"
    assert int(goalie["glove_high"]) == 85
    assert goalie["card_id"] == "G1001"
    assert skater["position"] == "RW"
    assert skater["card_id"] == "1001"


def test_sync_dedups_duplicate_card_ids():
    """The site can serve the same card on two pages; sync must drop the later
    duplicate so (snapshot_date, card_id) stays unique."""
    raw = {"card_art": '<a id="1001">TROY TERRY</a>', "full_name": "Troy Terry",
           "position": "RW", "team": "ANA", "overall": "84"}

    class FakeScraper:
        def __init__(self, url):
            self.url = url

        def iter_all_cards(self):
            if "goalie" in self.url:
                return
            yield dict(raw)
            yield dict(raw)  # same card_id twice

    captured = {}

    def fake_write(self, ref, df, *, snapshot_date):
        captured["df"] = df
        return len(df)

    with patch("nhl_hut_bigquery.cli.HUTScraper", FakeScraper), \
         patch("nhl_hut_bigquery.cli.bigquery.Client"), \
         patch("nhl_hut_bigquery.cli.check_payload_size"), \
         patch("nhl_hut_bigquery.cli.BigQueryWriter.write_snapshot", new=fake_write), \
         patch("nhl_hut_bigquery.cli.RunsTable.create_table_if_missing"), \
         patch("nhl_hut_bigquery.cli.RunsTable.record"):
        ret = main(["sync", "--table", "p.d.hut", "--snapshot-date", "2026-06-02"])

    assert ret == 0
    assert len(captured["df"]) == 1  # deduped from 2 -> 1
