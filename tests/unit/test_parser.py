from nhl_hut_bigquery.parser import parse_card


def test_parses_skater_card():
    raw = {
        "card_art": '<a id="abc123" href="?id=abc123">AUSTON MATTHEWS</a>',
        "full_name": '<a id="abc123" href="?id=abc123">Auston Matthews</a>',
        "overall": "92",
        "position": "C",
        "team": "TOR",
        "card": "BA",
        "shooting": "94",
        "skating": "90",
    }
    row = parse_card(raw, snapshot_date="2026-05-22",
                     source_url="https://example.com")
    assert row["card_id"] == "abc123"
    assert row["player_full_name"] == "Auston Matthews"
    assert row["player_full_name_normalized"] == "AUSTON MATTHEWS"
    assert row["position"] == "C"
    assert row["team_abbrev"] == "TOR"
    assert row["overall"] == 92
    assert row["snapshot_date"] == "2026-05-22"
    # Skater-side fields should be populated (even if None from raw)
    assert "acceleration" in row
    # Goalie-only fields exist but are None for a skater
    assert row["glove_high"] is None


def test_parses_goalie_card_with_nulls_on_skater_fields():
    raw = {
        "card_art": '<a id="g1" href="?id=g1">CAREY PRICE</a>',
        "full_name": "Carey Price",
        "position": "G",
        "team": "MTL",
        "card": "BA",
        "overall": "94",
        "glove_high": "92",
        "five_hole": "89",
    }
    row = parse_card(raw, snapshot_date="2026-05-22",
                     source_url="https://example.com")
    assert row["position"] == "G"
    assert row["glove_high"] == 92
    assert row["five_hole"] == 89
    # Skater-only ratings must be None for a goalie
    assert row["wrist_shot_power"] is None
    assert row["hand_eye"] is None


def test_invalid_overall_returns_none():
    raw = {
        "card_art": '<a id="x1">Player</a>',
        "full_name": "Player",
        "overall": "abc",
    }
    row = parse_card(raw, snapshot_date="2026-05-22",
                     source_url="https://example.com")
    assert row["overall"] is None


def test_strips_html_from_name():
    raw = {
        "card_art": '<a id="x2">Player X</a>',
        "full_name": "<b>Player</b> <i>X</i>",
        "overall": "80",
    }
    row = parse_card(raw, snapshot_date="2026-05-22",
                     source_url="https://example.com")
    assert row["player_full_name"] == "Player X"


def test_goalie_endpoint_shape_requires_force_position():
    """The real goalie endpoint omits `position`; without force_position the row
    is mis-parsed as a skater (goalie ratings dropped). With force_position='G'
    it parses correctly and the card_id is namespaced to dodge skater collisions."""
    raw = {  # mirrors goalie_stats.php: NO 'position' key
        "card_art": '<a id="1001">LUKAS DOSTAL</a>',
        "full_name": "Lukas Dostal",
        "team": "ANA",
        "overall": "81",
        "glove_high": "85",
        "five_hole": "80",
        "speed": "83",  # shared skater/goalie field
    }

    # Regression: without the override it's detected as a skater, goalie cols lost.
    misparsed = parse_card(raw, snapshot_date="2026-06-02",
                           source_url="https://x/goalie_stats.php")
    assert misparsed["position"] is None
    assert misparsed["glove_high"] is None

    # With force_position='G': correct goalie parse.
    row = parse_card(raw, snapshot_date="2026-06-02",
                     source_url="https://x/goalie_stats.php", force_position="G")
    assert row["position"] == "G"
    assert row["glove_high"] == 85
    assert row["five_hole"] == 80
    assert row["speed"] == 83
    assert row["wrist_shot_power"] is None  # skater-only nulled for goalies
    assert row["card_id"] == "G1001"        # namespaced


def test_skater_card_id_not_namespaced():
    raw = {
        "card_art": '<a id="1001">TROY TERRY</a>',
        "full_name": "Troy Terry",
        "position": "RW",
        "team": "ANA",
        "overall": "84",
    }
    row = parse_card(raw, snapshot_date="2026-06-02",
                     source_url="https://x/player_stats.php")
    assert row["card_id"] == "1001"  # skater ids stay bare
    assert row["position"] == "RW"
