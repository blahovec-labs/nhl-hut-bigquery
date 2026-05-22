"""Tests for HUTScraper — polite paginated client."""

import json

import responses as responses_lib

from nhl_hut_bigquery.client import HUTScraper

_URL = "https://nhlhutbuilder.com/NHL26/php/player_stats.php"


def _make_card(i: int) -> dict:
    """Return a minimal card dict with a unique row number."""
    return {"": str(i), "full_name": f"<a id=\"{1000 + i}\">PLAYER {i}</a>", "overall": "80"}


def _page_body(cards: list[dict], draw: int = 1) -> str:
    payload = {
        "draw": draw,
        "recordsTotal": 4,
        "recordsFiltered": 4,
        "data": cards,
    }
    return json.dumps(payload)


@responses_lib.activate
def test_iter_all_cards_paginates():
    """Two pages of 2 cards + 1 empty page → yields 4 cards total (not 3, per fixture)."""
    # Page 1: start=0 → 2 cards
    responses_lib.add(
        responses_lib.POST,
        _URL,
        body=_page_body([_make_card(0), _make_card(1)]),
        content_type="application/json",
    )
    # Page 2: start=2 → 2 cards
    responses_lib.add(
        responses_lib.POST,
        _URL,
        body=_page_body([_make_card(2), _make_card(3)]),
        content_type="application/json",
    )
    # Page 3: start=4 → empty → stop
    responses_lib.add(
        responses_lib.POST,
        _URL,
        body=_page_body([]),
        content_type="application/json",
    )

    scraper = HUTScraper(url=_URL, page_size=2, sleep_seconds=0.0)
    cards = list(scraper.iter_all_cards())
    assert len(cards) == 4


@responses_lib.activate
def test_iter_all_cards_stops_at_safety_cap():
    """Infinite pages with safety_cap=10 → only 10 cards yielded."""
    # Return 5 cards per page indefinitely (responses loops last matcher)
    page_cards = [_make_card(i) for i in range(5)]
    responses_lib.add(
        responses_lib.POST,
        _URL,
        body=_page_body(page_cards),
        content_type="application/json",
    )
    # Register extra copies so responses doesn't run out before 10 cards
    for _ in range(10):
        responses_lib.add(
            responses_lib.POST,
            _URL,
            body=_page_body(page_cards),
            content_type="application/json",
        )

    scraper = HUTScraper(url=_URL, page_size=5, sleep_seconds=0.0, safety_cap=10)
    cards = list(scraper.iter_all_cards())
    assert len(cards) == 10
