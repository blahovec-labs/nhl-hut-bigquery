"""HUTScraper — polite paginated client for nhlhutbuilder.com.

Sends POST requests to the DataTables server-side JSON endpoint, paging
through all cards at ``page_size`` rows per request with a configurable
inter-page sleep to avoid hammering the server.

SSL verification is disabled by default because the site has a cert
revocation issue; InsecureRequestWarning is suppressed at module level.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterator
from typing import Any

import requests
import urllib3

# Suppress the inevitable InsecureRequestWarning produced when verify=False.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _default_referer(url: str) -> str:
    """Derive a Referer from the PHP endpoint URL.

    Replaces ``/php/<something>.php`` with ``/<something>.php`` to produce
    the canonical page URL.

    Example:
        ``https://nhlhutbuilder.com/NHL26/php/player_stats.php``
        → ``https://nhlhutbuilder.com/NHL26/player-stats.php``

    Falls back to the URL as-is if the pattern doesn't match.
    """
    match = re.search(r"(/php/(\w+)\.php)$", url)
    if match:
        # Convert underscore path component to hyphen for the page URL.
        page = match.group(2).replace("_", "-")
        base = url[: match.start()]
        return f"{base}/{page}.php"
    return url


class HUTScraper:
    """Paginate the nhlhutbuilder.com DataTables endpoint and yield every card.

    Parameters
    ----------
    url:
        Full POST endpoint URL (player or goalie).
    user_agent:
        Value for the ``User-Agent`` header.
    page_size:
        Number of rows to request per page (``length`` parameter).
    sleep_seconds:
        Seconds to sleep *between* pages (not before the first request).
    timeout_seconds:
        HTTP request timeout in seconds.
    safety_cap:
        Hard upper bound on total cards yielded; prevents runaway loops.
    verify_ssl:
        Pass ``False`` to skip SSL verification (required for this site).
    referer:
        Override the ``Referer`` header; auto-derived from *url* if ``None``.
    """

    def __init__(
        self,
        url: str = "https://nhlhutbuilder.com/NHL26/php/player_stats.php",
        user_agent: str = "nhl-hut-bigquery/0.1 (research)",
        page_size: int = 100,
        sleep_seconds: float = 1.5,
        timeout_seconds: float = 30.0,
        safety_cap: int = 50_000,
        verify_ssl: bool = False,
        referer: str | None = None,
    ) -> None:
        self._url = url
        self._user_agent = user_agent
        self._page_size = page_size
        self._sleep_seconds = sleep_seconds
        self._timeout_seconds = timeout_seconds
        self._safety_cap = safety_cap
        self._verify_ssl = verify_ssl
        self._referer = referer if referer is not None else _default_referer(url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_page(self, start: int) -> list[dict[str, Any]]:
        """POST one page request and return the ``data`` list.

        Parameters
        ----------
        start:
            Zero-based row offset.

        Returns
        -------
        list[dict]
            The ``data`` array from the DataTables JSON response.
        """
        headers = {
            "User-Agent": self._user_agent,
            "Referer": self._referer,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        body = {
            "draw": "1",
            "start": str(start),
            "length": str(self._page_size),
        }
        response = requests.post(
            self._url,
            data=body,
            headers=headers,
            timeout=self._timeout_seconds,
            verify=self._verify_ssl,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return list(payload.get("data", []))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def iter_all_cards(self) -> Iterator[dict[str, Any]]:
        """Yield every card from the endpoint, page by page.

        Stops when:
        - A page returns an empty ``data`` list, or
        - ``safety_cap`` total cards have been yielded.

        No sleep is inserted before the *first* request; subsequent pages
        are separated by ``sleep_seconds``.
        """
        total_yielded = 0
        start = 0
        first_page = True

        while True:
            if not first_page and self._sleep_seconds > 0:
                time.sleep(self._sleep_seconds)
            first_page = False

            cards = self._fetch_page(start)
            if not cards:
                break

            for card in cards:
                if total_yielded >= self._safety_cap:
                    return
                yield card
                total_yielded += 1

            start += self._page_size
