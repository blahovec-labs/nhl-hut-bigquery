"""Parse raw HUT card records into schema-aligned rows.

Field names match the ACTUAL NHL26 API response keys confirmed in Task 1 recon.
Skaters come from player_stats.php; goalies from goalie_stats.php.
Both are collapsed into a single unified row shape per HUT_RATINGS_SCHEMA.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from unidecode import unidecode

# ---------------------------------------------------------------------------
# Rating column lists — must exactly match HUT_RATINGS_SCHEMA field names.
# ---------------------------------------------------------------------------

# 24 skater attribute columns (NULL for goalie rows).
# Six of these (passing, speed, endurance, agility, aggression, durability)
# also appear in the goalie endpoint; they share the same column.
_SKATER_RATINGS: tuple[str, ...] = (
    "acceleration",
    "agility",
    "balance",
    "endurance",
    "speed",
    "slap_shot_accuracy",
    "slap_shot_power",
    "wrist_shot_accuracy",
    "wrist_shot_power",
    "deking",
    "hand_eye",
    "passing",
    "puck_control",
    "off_awareness",
    "def_awareness",
    "body_checking",
    "strength",
    "aggression",
    "durability",
    "fighting_skill",
    "shot_blocking",
    "stick_checking",
    "faceoffs",
    "discipline",
)

# 11 goalie-only attribute columns (NULL for skater rows).
_GOALIE_ONLY_RATINGS: tuple[str, ...] = (
    "glove_high",
    "stick_high",
    "glove_low",
    "stick_low",
    "poke_check",
    "vision",
    "positioning",
    "five_hole",
    "breakaway",
    "shot_recovery",
    "rebound_control",
)

# Skater-only columns that must be NULL when position == "G".
# The six shared columns (passing, speed, endurance, agility, aggression,
# durability) are populated from both endpoints.
_SKATER_ONLY_RATINGS: frozenset[str] = frozenset(_SKATER_RATINGS) - frozenset(
    ("passing", "speed", "endurance", "agility", "aggression", "durability")
)

# Sentinel date value used by the HUT API to mean "unknown date".
_DATE_SENTINEL = "0000-00-00"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def normalize_name(value: str | None) -> str | None:
    """UPPER-case, accent-fold, strip non-alphanumeric (except spaces), collapse whitespace.

    Returns None for None or empty/whitespace-only input.

    Examples:
        "Auston Matthews"  -> "AUSTON MATTHEWS"
        "Léo Carlsson"     -> "LEO CARLSSON"
        "J.T. Miller"      -> "JT MILLER"
        "D'Angelo Rondo"   -> "DANGELO RONDO"
        "  John   Doe  "   -> "JOHN DOE"
        None               -> None
    """
    if value is None:
        return None
    folded = unidecode(value)
    # Strip everything that isn't a letter, digit, or space
    cleaned = re.sub(r"[^A-Za-z0-9 ]", "", folded)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.upper() if cleaned else None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _strip_html(value: str | None) -> str | None:
    """Remove HTML tags and collapse whitespace. Returns None for empty/None."""
    if value is None:
        return None
    stripped = re.sub(r"<[^>]+>", " ", value)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped if stripped else None


def _to_int(value: Any) -> int | None:
    """Parse integer from string/int/None. Returns None on failure."""
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    """Parse float from string/float/None. Returns None on failure."""
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def _parse_card_id_from_html(html: str | None) -> str | None:
    """Extract the id= attribute value from a card_art HTML anchor.

    Example input:  '<a id="1001" href="?id=1001" ...>TROY TERRY</a>'
    Returns:        '1001'

    Accepts numeric-only ids (typical production) and alphanumeric ids
    (e.g. test fixtures). Matches the first id= attribute in the string.
    """
    if not html:
        return None
    # Try numeric-only first (production shape: id="1001")
    m = re.search(r'id=["\'](\d+)["\']', html)
    if m:
        return m.group(1)
    # Fall back to any word-char id (handles test fixtures like id="abc123")
    m = re.search(r'id=["\'](\w+)["\']', html)
    return m.group(1) if m else None


def _sentinel_date(value: Any) -> str | None:
    """Convert HUT date strings, treating the '0000-00-00' sentinel as None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s == _DATE_SENTINEL:
        return None
    return s


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------


def parse_card(
    raw: dict[str, Any],
    *,
    snapshot_date: str,
    source_url: str,
    force_position: str | None = None,
) -> dict[str, Any]:
    """Convert one raw HUT card dict into a schema-aligned row dict.

    Always returns all schema columns; absent or unparseable values become None.

    The goalie endpoint (goalie_stats.php) does NOT return a ``position`` field,
    so callers scraping it must pass ``force_position="G"``. Otherwise the row is
    mis-detected as a skater and all 11 goalie-only ratings are nulled.

    Priority for card_id:
      1. Parse id= attribute from raw["card_art"] HTML
      2. raw["card_id"]
      3. raw["id"]
      4. raw["unique_id"]
      5. Empty string (caller may flag for diagnostics)

    Goalie card_ids are namespaced with a ``"G"`` prefix: the skater and goalie
    endpoints each number their rows independently (both start near 1000), so a
    bare id collides across endpoints and breaks the (snapshot_date, card_id) key.
    """
    # The goalie endpoint omits `position`; force_position lets the caller tag
    # goalie rows by endpoint. Fall back to the raw card's value for skaters.
    position = force_position if force_position is not None else raw.get("position")
    is_goalie = str(position or "").strip().upper() == "G"

    # --- card_id -------------------------------------------------------
    card_id = (
        _parse_card_id_from_html(raw.get("card_art"))
        or str(raw.get("card_id") or raw.get("id") or raw.get("unique_id") or "")
    )
    # Namespace goalie ids to avoid cross-endpoint collisions with skater ids.
    if is_goalie and card_id:
        card_id = f"G{card_id}"

    # --- player_full_name (HTML-stripped) --------------------------------
    name_raw = raw.get("full_name") or raw.get("player_name")
    player_full_name = _strip_html(str(name_raw)) if name_raw is not None else None

    row: dict[str, Any] = {
        # Snapshot identity
        "snapshot_date": snapshot_date,
        "card_id": card_id,
        "ingested_at": datetime.now(UTC),
        # Player identity
        "player_full_name": player_full_name,
        "player_full_name_normalized": normalize_name(player_full_name),
        "nhl_player_id": _to_int(raw.get("nhl_player_id")),
        "position": position,
        "team_abbrev": raw.get("team") or raw.get("team_abbrev"),
        "nationality": raw.get("nationality") or raw.get("country"),
        # Card metadata
        "card": raw.get("card") or raw.get("card_set"),
        "league": raw.get("league"),
        "division": raw.get("division"),
        "salary": _strip_html(str(raw.get("salary"))) if raw.get("salary") is not None else None,
        "hand": raw.get("hand"),
        "weight": _strip_html(str(raw.get("weight"))) if raw.get("weight") is not None else None,
        "height": raw.get("height"),
        "date_added": _sentinel_date(raw.get("date_added")),
        "date_updated": _sentinel_date(raw.get("date_updated")),
        # Overall ratings
        "overall": _to_int(raw.get("overall")),
        "aOVR": _to_float(raw.get("aOVR") or raw.get("aovr")),
        # Diagnostic
        "source_url": source_url,
        "raw_html_snippet": None,
    }

    # --- Skater attribute ratings (24 cols) ------------------------------
    # For goalies: skater-only cols are NULL; shared cols (passing, speed, etc.)
    # are populated from the goalie endpoint's fields.
    for field in _SKATER_RATINGS:
        if is_goalie and field in _SKATER_ONLY_RATINGS:
            row[field] = None
        else:
            row[field] = _to_int(raw.get(field))

    # --- Goalie-only attribute ratings (11 cols) -------------------------
    # For skaters: all goalie-only cols are NULL.
    for field in _GOALIE_ONLY_RATINGS:
        if is_goalie:
            row[field] = _to_int(raw.get(field))
        else:
            row[field] = None

    return row


# ---------------------------------------------------------------------------
# Trip-wires
# ---------------------------------------------------------------------------


def check_payload_size(
    *,
    card_count: int,
    min_expected: int = 50,
    max_expected: int = 50_000,
) -> None:
    """Fail fast on degenerate scrape payloads.

    Raises ValueError if card_count is outside [min_expected, max_expected].
    Returns None on success.
    """
    if card_count < min_expected:
        raise ValueError(
            f"trip-wire: too few cards ({card_count} < {min_expected}). "
            "The HUT endpoint may have changed; do not write a partial snapshot."
        )
    if card_count > max_expected:
        raise ValueError(
            f"trip-wire: too many cards ({card_count} > {max_expected}). "
            "Pagination or duplicate-detection logic may be broken."
        )
