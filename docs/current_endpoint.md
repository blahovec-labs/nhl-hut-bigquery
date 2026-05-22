# HUT current endpoint (as of 2026-05-22)

## Endpoint

- **Player stats URL:** `https://nhlhutbuilder.com/NHL26/php/player_stats.php`
- **Goalie stats URL:** `https://nhlhutbuilder.com/NHL26/php/goalie_stats.php`
- **Method:** POST
- **Content-Type:** `application/x-www-form-urlencoded`
- **Body/params (DataTables server-side protocol):**
  - `draw=1` — DataTables request sequence number (echo'd back in response)
  - `start=0` — offset (0-based)
  - `length=100` — page size (max tested: works up to at least 5741)
- **Headers (besides User-Agent):**
  - `Referer: https://nhlhutbuilder.com/NHL26/player-stats.php`

### Notes on version path

The site hosts multiple game years under versioned subdirectories:
- `/NHL25/php/player_stats.php` — still live; returns 5,137 cards (NHL 25 season data)
- `/NHL26/php/player_stats.php` — current season; returns 5,741 cards

The root `https://nhlhutbuilder.com/` redirects to the NHL26 context for the current season links. Target `NHL26` for all new ingestion.

## Response shape

DataTables server-side JSON format:

```json
{
  "draw": 1,
  "recordsTotal": 5741,
  "recordsFiltered": 5741,
  "data": [
    {
      "": "0",
      "card_art": "<a id=\"1001\" href=\"?id=1001\" class=\"advanced-stats\"><img src=\"images/card_art/players/100107092025091229.jpg\" width=\"100px\"/></a>",
      "card": "BA",
      "nationality": "USA",
      "league": "NHL",
      "team": "ANA",
      "division": "Pacific",
      "position": "RW",
      "salary": "$5.0M",
      "hand": "RIGHT",
      "weight": "191<span class=\"lower\"> lb</span>",
      "height": "6' 0\"",
      "full_name": "<a id=\"1001\" href=\"?id=1001\" class=\"advanced-stats\">TROY TERRY</a>",
      "overall": "84",
      "aOVR": "84.90",
      "deking": "88",
      "hand_eye": "88",
      "passing": "86",
      "puck_control": "88",
      "slap_shot_accuracy": "87",
      "slap_shot_power": "86",
      "wrist_shot_accuracy": "88",
      "wrist_shot_power": "86",
      "acceleration": "88",
      "agility": "87",
      "balance": "83",
      "endurance": "81",
      "speed": "88",
      "discipline": "82",
      "off_awareness": "84",
      "def_awareness": "81",
      "faceoffs": "68",
      "shot_blocking": "78",
      "stick_checking": "83",
      "aggression": "82",
      "body_checking": "83",
      "durability": "83",
      "fighting_skill": "62",
      "strength": "83",
      "date_added": "2025-09-07",
      "date_updated": "0000-00-00"
    }
  ]
}
```

All numeric stat values are returned as **strings** (not integers). `aOVR` is a float string. `weight`, `height`, `salary`, `full_name`, and `card_art` contain embedded HTML and must be stripped before loading into BigQuery.

## Per-card fields available (player endpoint)

Metadata / identity:
- `""` (unnamed) — always `"0"`; appears to be a placeholder column, ignore
- `card_art` — HTML anchor+img with numeric `id` attribute; parse for `card_id`
- `card` — card type code (e.g., `BA`, `CAP`, `FI`, `HH`, `ICON`, `GOG`, `GB`, `GM`, `HUTC`, `TOTW`)
- `nationality` — country name string
- `league` — e.g., `"NHL"`
- `team` — 3-letter team abbreviation
- `division` — conference division name
- `position` — e.g., `"RW"`, `"C"`, `"LW"`, `"RD"`, `"LD"`
- `salary` — HTML string, e.g., `"$5.0M"` (cap hit)
- `hand` — `"LEFT"` or `"RIGHT"`
- `weight` — HTML string, e.g., `"191<span class=\"lower\"> lb</span>"`
- `height` — string, e.g., `"6' 0\""`
- `full_name` — HTML anchor with player name; parse inner text for clean name
- `date_added` — ISO date `YYYY-MM-DD`
- `date_updated` — ISO date `YYYY-MM-DD`; `"0000-00-00"` when never updated

Ratings (all returned as numeric strings, range 0–99):
- `overall` — overall rating (integer string)
- `aOVR` — average OVR (float string, e.g., `"84.90"`)
- `acceleration`
- `agility`
- `balance`
- `endurance`
- `speed`
- `slap_shot_accuracy`
- `slap_shot_power`
- `wrist_shot_accuracy`
- `wrist_shot_power`
- `deking`
- `off_awareness`
- `hand_eye`
- `passing`
- `puck_control`
- `body_checking`
- `strength`
- `aggression`
- `durability`
- `fighting_skill`
- `def_awareness`
- `shot_blocking`
- `stick_checking`
- `faceoffs`
- `discipline`

**Total: 40 keys** (39 meaningful + 1 unnamed placeholder)

## Goalie endpoint fields (bonus — `NHL26/php/goalie_stats.php`)

666 goalie cards. Fields: `""`, `card_art`, `nationality`, `card`, `league`, `team`, `division`, `salary`, `hand`, `weight`, `height`, `full_name`, `overall`, `glove_high`, `stick_high`, `glove_low`, `poke_check`, `stick_low`, `passing`, `speed`, `vision`, `endurance`, `agility`, `positioning`, `five_hole`, `breakaway`, `shot_recovery`, `aggression`, `rebound_control`, `durability`, `date_added`, `date_updated`

## Natural key candidate

**`card_id`** — the numeric integer embedded in the `card_art` anchor's `id` attribute and in the `full_name` anchor's `id` attribute. Example: `<a id="1001" ...>` → `card_id = 1001`. This ID is stable across requests and unique per card row. It is also used in the detail URL `player-stats.php?id=1001`.

Extraction regex: `re.search(r'id="(\d+)"', row['card_art']).group(1)`

For snapshot dedup in BigQuery: use `(card_id, snapshot_date)` as the composite key. `date_updated` is unreliable (`"0000-00-00"` on most cards); prefer `date_added` + snapshot timestamp for change detection.

## Observed card type codes (from sampling)

Early pages (BA era): `BA`, `CAP`, `FI`, `HH`, `ICON`  
Late pages (May 2026 additions): `GB`, `GM`, `GOG`, `HUTC`, `TOTW`

`BA` = Base; `TOTW` = Team of the Week; `GOG` = Greatest of all time; others TBD.

## Approximate total card count

| Endpoint | Total cards | As of |
|---|---|---|
| `NHL26/php/player_stats.php` | **5,741** | 2026-05-22 |
| `NHL26/php/goalie_stats.php` | **666** | 2026-05-22 |
| `NHL25/php/player_stats.php` | 5,137 | 2026-05-22 (historical) |

Combined NHL26 skaters + goalies: **6,407 cards**

## Pagination

The endpoint is fully pageable via `start` + `length`. A single pull of all 5,741 rows with `length=6000` is feasible (tested conceptually; response size ~2–3 MB). Recommended scrape strategy: single request with `length=10000` to capture all records atomically per snapshot run.
