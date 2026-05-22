"""Four matchers + the resolver ladder.

Each matcher takes:
  hut    : dict with normalized HUT fields
  nhl_dim: pandas DataFrame columns:
           player_id, full_name_normalized, position_code, team_abbrevs (list[str])

Each matcher returns (player_id | None, confidence) where confidence is
1.0 / 0.95 / 0.85 / 0.70 / 0.00 per the spec ladder.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def match_nhl_id_direct(
    hut: dict[str, Any],
    nhl_dim: pd.DataFrame,
) -> tuple[int | None, float]:
    """Direct NHL player_id match — confidence 1.0."""
    pid = hut.get("nhl_player_id")
    if pid is None:
        return (None, 0.0)
    return (int(pid), 1.0)


def match_exact_name_team_season(
    hut: dict[str, Any],
    nhl_dim: pd.DataFrame,
) -> tuple[int | None, float]:
    """Exact normalized name + team abbrev match — confidence 0.95.

    hut.team_abbrev must appear in nhl_dim.team_abbrevs (list[str]) to handle
    players who appeared on multiple teams during the season.
    """
    name = hut.get("player_full_name_normalized")
    team = hut.get("team_abbrev")
    if not name or not team or nhl_dim.empty:
        return (None, 0.0)
    cand = nhl_dim[
        (nhl_dim["full_name_normalized"] == name)
        & nhl_dim["team_abbrevs"].apply(lambda ts: team in (ts or []))
    ]
    if len(cand) == 1:
        return (int(cand.iloc[0]["player_id"]), 0.95)
    return (None, 0.0)


def match_exact_name_position_season(
    hut: dict[str, Any],
    nhl_dim: pd.DataFrame,
) -> tuple[int | None, float]:
    """Exact normalized name + position code match — confidence 0.85.

    Useful when the HUT team differs from NHL team (e.g. mid-season trade).
    """
    name = hut.get("player_full_name_normalized")
    pos = hut.get("position")
    if not name or not pos or nhl_dim.empty:
        return (None, 0.0)
    cand = nhl_dim[
        (nhl_dim["full_name_normalized"] == name)
        & (nhl_dim["position_code"] == pos)
    ]
    if len(cand) == 1:
        return (int(cand.iloc[0]["player_id"]), 0.85)
    return (None, 0.0)


def match_exact_name_season(
    hut: dict[str, Any],
    nhl_dim: pd.DataFrame,
) -> tuple[int | None, float]:
    """Exact normalized name match with no other filters — confidence 0.70.

    Only succeeds when the name is unique across the entire season's player dim.
    """
    name = hut.get("player_full_name_normalized")
    if not name or nhl_dim.empty:
        return (None, 0.0)
    cand = nhl_dim[nhl_dim["full_name_normalized"] == name]
    if len(cand) == 1:
        return (int(cand.iloc[0]["player_id"]), 0.70)
    return (None, 0.0)


_LADDER: tuple[tuple[str, Any], ...] = (
    ("nhl_id_direct", match_nhl_id_direct),
    ("exact_name_team_season", match_exact_name_team_season),
    ("exact_name_position_season", match_exact_name_position_season),
    ("exact_name_season", match_exact_name_season),
)


def resolve_card(
    hut: dict[str, Any],
    nhl_dim: pd.DataFrame,
) -> tuple[int | None, str, float]:
    """Walk the match ladder. First method returning a single match wins.

    Returns:
        (player_id, method_name, confidence)
        (None, "unmatched", 0.0) when all methods fail.
    """
    for method, fn in _LADDER:
        pid, conf = fn(hut, nhl_dim)
        if pid is not None:
            return (pid, method, conf)
    return (None, "unmatched", 0.0)
