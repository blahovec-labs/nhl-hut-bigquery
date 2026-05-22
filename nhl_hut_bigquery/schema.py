"""ColumnSpec for HUT ratings schema — same dataclass as nhl-bigquery
with field renames for the HUT source.

GOALIE ENDPOINT STRATEGY (v0.1):
  Skaters come from NHL26/php/player_stats.php (5,741 cards).
  Goalies come from NHL26/php/goalie_stats.php (666 cards) — a *separate* endpoint
  with a different field set.  Both are stored in one unified table:
    - All 24 skater rating columns are present; NULL for goalie rows.
    - Goalie-only columns (glove_high, stick_high, glove_low, poke_check, stick_low,
      vision, positioning, five_hole, breakaway, shot_recovery, rebound_control)
      are present; NULL for skater rows.
    - Six rating fields that appear in BOTH endpoints (passing, speed, endurance,
      agility, aggression, durability) use a single unified column — the parser
      populates it from whichever endpoint produced the row.
  The parser (Task 5) must fetch both endpoints and tag each row's position
  appropriately so downstream consumers can filter by position.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SCHEMA_VERSION = "0.1.0"

BqType = Literal[
    "INT64", "FLOAT64", "STRING", "BOOL", "DATE", "TIMESTAMP", "TIME", "NUMERIC",
]
BqMode = Literal["REQUIRED", "NULLABLE", "REPEATED"]

_VALID_TYPES = set(BqType.__args__)  # type: ignore[attr-defined]
_VALID_MODES = set(BqMode.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    type: BqType
    mode: BqMode
    short_description: str
    business_definition: str
    semantic_tags: list[str]
    valid_range: tuple[float, float] | None
    valid_values: list[str] | None
    example_value: object | None
    gotchas: list[str]
    nhlhutbuilder_field_equivalent: str | None
    nhlhutbuilder_source_field: str
    deprecated_in_year: int | None

    def __post_init__(self) -> None:
        if self.type not in _VALID_TYPES:
            raise ValueError(f"{self.name}: invalid type {self.type!r}")
        if self.mode not in _VALID_MODES:
            raise ValueError(f"{self.name}: invalid mode {self.mode!r}")
        if not self.business_definition.strip():
            raise ValueError(f"{self.name}: business_definition required")


@dataclass(frozen=True)
class PartitioningSpec:
    field: str
    type: Literal["DAY", "MONTH", "YEAR"]
    clustering: list[str]


def _col(name, type, mode, short, defn, *, tags=None, range_=None, values=None,
         example=None, gotchas=None, src=None, eq=None, dep=None):
    """Helper to compactly construct ColumnSpec instances."""
    return ColumnSpec(
        name=name, type=type, mode=mode,
        short_description=short, business_definition=defn,
        semantic_tags=list(tags or []),
        valid_range=range_, valid_values=values, example_value=example,
        gotchas=list(gotchas or []),
        nhlhutbuilder_field_equivalent=eq,
        nhlhutbuilder_source_field=src or name,
        deprecated_in_year=dep,
    )


# ---------------------------------------------------------------------------
# Partitioning
# ---------------------------------------------------------------------------

def get_partitioning() -> PartitioningSpec:
    """Return the BigQuery partitioning + clustering spec for hut_player_ratings."""
    return PartitioningSpec(
        field="snapshot_date",
        type="DAY",
        clustering=["position", "overall"],
    )


# ---------------------------------------------------------------------------
# HUT_RATINGS_SCHEMA
# Field names are the ACTUAL API field names confirmed by NHL26 recon (Task 1).
# Skater endpoint: 5,741 cards  |  Goalie endpoint: 666 cards (separate POST).
# ---------------------------------------------------------------------------

# 24 skater attribute fields — exact names from player_stats.php JSON response
_SKATER_RATING_FIELDS = (
    # Speed / skating
    "acceleration",
    "agility",
    "balance",
    "endurance",
    "speed",
    # Shooting
    "slap_shot_accuracy",
    "slap_shot_power",
    "wrist_shot_accuracy",
    "wrist_shot_power",
    # Puck skills
    "deking",
    "hand_eye",
    "passing",
    "puck_control",
    # Awareness
    "off_awareness",
    "def_awareness",
    # Physical
    "body_checking",
    "strength",
    "aggression",
    "durability",
    "fighting_skill",
    # Defense / specialty
    "shot_blocking",
    "stick_checking",
    "faceoffs",
    "discipline",
)

# Goalie-only fields — from goalie_stats.php; NULL for all skater rows.
# Six fields overlap with skater names (passing, speed, endurance, agility,
# aggression, durability) — those use the unified skater columns above.
_GOALIE_ONLY_FIELDS = (
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

# Human-readable labels for skater ratings (used in short_description)
_SKATER_LABELS: dict[str, str] = {
    "acceleration": "Acceleration",
    "agility": "Agility",
    "balance": "Balance",
    "endurance": "Endurance",
    "speed": "Speed",
    "slap_shot_accuracy": "Slap Shot Accuracy",
    "slap_shot_power": "Slap Shot Power",
    "wrist_shot_accuracy": "Wrist Shot Accuracy",
    "wrist_shot_power": "Wrist Shot Power",
    "deking": "Deking",
    "hand_eye": "Hand Eye",
    "passing": "Passing",
    "puck_control": "Puck Control",
    "off_awareness": "Offensive Awareness",
    "def_awareness": "Defensive Awareness",
    "body_checking": "Body Checking",
    "strength": "Strength",
    "aggression": "Aggression",
    "durability": "Durability",
    "fighting_skill": "Fighting Skill",
    "shot_blocking": "Shot Blocking",
    "stick_checking": "Stick Checking",
    "faceoffs": "Faceoffs",
    "discipline": "Discipline",
}

_GOALIE_LABELS: dict[str, str] = {
    "glove_high": "Glove High",
    "stick_high": "Stick High",
    "glove_low": "Glove Low",
    "stick_low": "Stick Low",
    "poke_check": "Poke Check",
    "vision": "Vision",
    "positioning": "Positioning",
    "five_hole": "Five Hole",
    "breakaway": "Breakaway",
    "shot_recovery": "Shot Recovery",
    "rebound_control": "Rebound Control",
}

HUT_RATINGS_SCHEMA: list[ColumnSpec] = [
    # ------------------------------------------------------------------
    # Snapshot identity (3 cols)
    # ------------------------------------------------------------------
    _col("snapshot_date", "DATE", "REQUIRED",
         "Date this snapshot was captured.",
         "Calendar date (ET) when this scrape run was executed. Partition key. "
         "Combined with card_id forms the composite natural key for dedup.",
         tags=["temporal", "identifier"], example="2026-05-22",
         src="(set by sync)"),
    _col("card_id", "STRING", "REQUIRED",
         "Stable HUT card identifier.",
         "Numeric string parsed from the id= attribute of the card_art HTML anchor "
         "in the API response (e.g. <a id=\"1001\" ...> → card_id = '1001'). "
         "Stable across requests and unique per card. Combined with snapshot_date "
         "forms the composite natural key. Extraction: "
         "re.search(r'id=(\")(\\d+)\\1', row['card_art']).group(2).",
         tags=["identifier", "join_key"], example="1001",
         src="card_art (parsed)",
         eq="id attribute of card_art anchor"),
    _col("ingested_at", "TIMESTAMP", "REQUIRED",
         "UTC timestamp when this row was written.",
         "Wall-clock UTC timestamp set by the sync process at write time. "
         "Not sourced from the API — set server-side.",
         tags=["meta"], example="2026-05-22T17:00:00Z",
         src="(set by sync)"),

    # ------------------------------------------------------------------
    # Player identity (6 cols)
    # ------------------------------------------------------------------
    _col("player_full_name", "STRING", "NULLABLE",
         "Player display name (HTML-stripped).",
         "Full display name parsed from the full_name HTML anchor in the API response "
         "after stripping tags. Example raw: "
         "<a id=\"1001\" href=\"?id=1001\" class=\"advanced-stats\">TROY TERRY</a>. "
         "Stored verbatim (no case normalisation).",
         tags=["identifier"], example="TROY TERRY",
         src="full_name (HTML inner text)", eq="full_name"),
    _col("player_full_name_normalized", "STRING", "NULLABLE",
         "Accent-folded, uppercased name for fuzzy joins.",
         "UPPER-cased, Unidecode accent-folded, punctuation-stripped version of "
         "player_full_name. Used as fallback join key against nhl-bigquery's "
         "player dimension when no direct nhl_player_id is available.",
         tags=["identifier", "join_key", "derived"],
         example="TROY TERRY",
         src="(derived from player_full_name)"),
    _col("nhl_player_id", "INT64", "NULLABLE",
         "NHL player ID (if exposed by HUT site).",
         "NHL/MLBAM-style numeric player_id if the HUT site exposes it directly. "
         "As of NHL26 recon, the site does NOT expose this field — it is NULL for all "
         "rows. Downstream resolver (Task 11) backfills via hut_player_xref.",
         tags=["identifier", "join_key"], example=None,
         src="nhl_player_id (not present in NHL26 endpoint)"),
    _col("position", "STRING", "NULLABLE",
         "Player position code.",
         "Position code from the HUT API: C, LW, RW, LD, RD for skaters; G absent "
         "from the skater endpoint (goalies come from a separate endpoint). "
         "The parser tags goalie rows with position=G after fetching goalie_stats.php.",
         tags=["identifier"],
         values=["C", "LW", "RW", "LD", "RD", "G"],
         example="RW",
         src="position"),
    _col("team_abbrev", "STRING", "NULLABLE",
         "Three-letter team abbreviation (HUT display).",
         "Team abbreviation as shown on the HUT card (API field: team). "
         "Represents the team the player was on when the card was released — "
         "may differ from the player's current NHL team.",
         tags=["identifier", "team"], example="ANA",
         src="team", eq="team"),
    _col("nationality", "STRING", "NULLABLE",
         "Player nationality (HUT display).",
         "Country string shown on the HUT card, e.g. 'USA', 'CAN', 'SWE'.",
         tags=["identifier"], example="USA",
         src="nationality"),

    # ------------------------------------------------------------------
    # Card metadata (8 cols)
    # ------------------------------------------------------------------
    _col("card", "STRING", "NULLABLE",
         "HUT card type code.",
         "Short code identifying the card program, e.g. BA=Base, TOTW=Team of the Week, "
         "GOG=Greatest of All Time, HUTC=HUT Champs, FI=Future Icons, ICON, HH, CAP, GB, GM. "
         "This is the direct 'card' field from the API response.",
         tags=["card_meta"], example="BA",
         src="card", eq="card"),
    _col("league", "STRING", "NULLABLE",
         "League shown on the HUT card.",
         "League string from the API, e.g. 'NHL'. Most cards are NHL but some "
         "international/minor-league cards appear.",
         tags=["card_meta"], example="NHL",
         src="league"),
    _col("division", "STRING", "NULLABLE",
         "Division shown on the HUT card.",
         "Division name from the API, e.g. 'Pacific', 'Atlantic'. "
         "Reflects the team's division at card-release time.",
         tags=["card_meta"], example="Pacific",
         src="division"),
    _col("salary", "STRING", "NULLABLE",
         "Cap hit salary string (HTML-stripped).",
         "Salary / cap hit displayed on the HUT card after stripping any HTML. "
         "Example raw: '$5.0M'. Stored as a string — parse to numeric downstream if needed.",
         tags=["card_meta"], example="$5.0M",
         src="salary"),
    _col("hand", "STRING", "NULLABLE",
         "Shooting/catching hand.",
         "LEFT or RIGHT as shown on the HUT card.",
         tags=["card_meta"], values=["LEFT", "RIGHT"], example="RIGHT",
         src="hand"),
    _col("weight", "STRING", "NULLABLE",
         "Player weight string (HTML-stripped).",
         "Weight string after stripping embedded HTML span. "
         "Example raw: '191<span class=\"lower\"> lb</span>' → '191 lb'.",
         tags=["card_meta"], example="191 lb",
         src="weight"),
    _col("height", "STRING", "NULLABLE",
         "Player height string.",
         "Height as shown on the HUT card, e.g. \"6' 0\\\"\". No HTML stripping needed.",
         tags=["card_meta"], example="6' 0\"",
         src="height"),
    _col("date_added", "DATE", "NULLABLE",
         "Date the card was added to HUT.",
         "Release date of this card in the game, from the date_added API field. "
         "Format: YYYY-MM-DD. '0000-00-00' is returned when unknown — "
         "the parser converts this sentinel to NULL.",
         tags=["temporal", "card_meta"], example="2025-09-07",
         src="date_added"),
    _col("date_updated", "DATE", "NULLABLE",
         "Date the card was last updated in HUT.",
         "Last-updated date from the date_updated API field. "
         "'0000-00-00' is returned on most cards (never updated) — "
         "the parser converts this sentinel to NULL. "
         "Unreliable for change-detection; prefer snapshot diffs instead.",
         tags=["temporal", "card_meta"], example=None,
         gotchas=["'0000-00-00' sentinel must be converted to NULL before BQ load"],
         src="date_updated"),

    # ------------------------------------------------------------------
    # Overall ratings (2 cols)
    # ------------------------------------------------------------------
    _col("overall", "INT64", "REQUIRED",
         "Card OVR rating (integer).",
         "The canonical HUT card overall rating, an integer typically in 60-99. "
         "All values are returned as numeric strings from the API and must be "
         "parsed to INT64.",
         tags=["measure", "rating"], range_=(60.0, 99.0), example=84,
         src="overall"),
    _col("aOVR", "FLOAT64", "NULLABLE",
         "Advanced / average OVR (float).",
         "Weighted average OVR computed by nhlhutbuilder.com, returned as a float "
         "string (e.g. '84.90'). Slightly higher or lower than the integer overall "
         "depending on attribute weights. NULL if absent.",
         tags=["measure", "rating"], range_=(60.0, 99.0), example=84.90,
         src="aOVR"),

    # ------------------------------------------------------------------
    # Skater attribute ratings (24 cols) — NULL for goalie rows
    # Field names match the EXACT keys in the player_stats.php JSON response.
    # ------------------------------------------------------------------
    *[
        _col(field, "INT64", "NULLABLE",
             f"Skater rating: {_SKATER_LABELS[field]}.",
             f"Skater attribute rating for {_SKATER_LABELS[field]}. "
             f"Integer 0-99, returned as a string from the API. NULL for goalie rows. "
             f"Six of these fields (passing, speed, endurance, agility, aggression, "
             f"durability) also appear in the goalie endpoint and use this same column.",
             tags=["measure", "rating", "skater"],
             range_=(0.0, 99.0), example=85,
             src=field, eq=field)
        for field in _SKATER_RATING_FIELDS
    ],

    # ------------------------------------------------------------------
    # Goalie-only attribute ratings (11 cols) — NULL for skater rows
    # Field names match the EXACT keys in the goalie_stats.php JSON response.
    # The six overlapping fields (passing, speed, endurance, agility, aggression,
    # durability) are handled by the skater columns above.
    # ------------------------------------------------------------------
    *[
        _col(field, "INT64", "NULLABLE",
             f"Goalie rating: {_GOALIE_LABELS[field]}.",
             f"Goalie-specific attribute rating for {_GOALIE_LABELS[field]}. "
             f"Integer 0-99, returned as a string from the goalie_stats.php API. "
             f"NULL for all skater rows.",
             tags=["measure", "rating", "goalie"],
             range_=(0.0, 99.0), example=88,
             src=field, eq=field)
        for field in _GOALIE_ONLY_FIELDS
    ],

    # ------------------------------------------------------------------
    # Diagnostic (2 cols)
    # ------------------------------------------------------------------
    _col("source_url", "STRING", "NULLABLE",
         "Source endpoint URL for this row.",
         "The API endpoint URL used to scrape this card row. Distinguishes "
         "skater rows (player_stats.php) from goalie rows (goalie_stats.php). "
         "Useful for tracking site changes over snapshot history.",
         tags=["meta", "diagnostic"],
         example="https://nhlhutbuilder.com/NHL26/php/player_stats.php",
         src="(set by sync)"),
    _col("raw_html_snippet", "STRING", "NULLABLE",
         "Raw HTML snippet captured on parse failure.",
         "Stores the raw card_art or full_name HTML string for any card that "
         "triggered a parse failure or trip-wire. NULL for cleanly parsed rows. "
         "Diagnostic only — not loaded into production queries.",
         tags=["meta", "diagnostic"], example=None,
         src="(set by sync on parse failure)"),
]
