# Changelog

## 0.1.1

First end-to-end run against real BigQuery surfaced (and fixed) six latent bugs;
v0.1.0's tests all mocked the network and BigQuery. Verified by ingesting 6,495
cards (5,828 skaters + 667 goalies) and resolving 59.6% to NHL player_ids via
`nhl-bigquery`'s `dim_players`.

- **Goalies were silently broken.** The goalie endpoint omits the `position`
  field, so `is_goalie` was always False and all 11 goalie-only ratings were
  nulled. `sync` now tags goalie rows via a new `force_position` arg per endpoint.
- **Goalie `card_id`s are namespaced (`G####`).** The skater and goalie endpoints
  number their rows independently and collided on `(snapshot_date, card_id)`.
- **`writer` coerces DataFrame dtypes before loading** (string→DATE, nullable
  Int64, TIMESTAMP) and passes the destination schema to the load job; a string
  `snapshot_date` could not be loaded into a DATE column.
- **The run-log table is no longer created schemaless.** `RunsTable.SCHEMA` was a
  dataclass field defaulting to `None`, which shadowed the class attribute; it is
  now a `ClassVar`.
- **`verify --aggregation snapshot-integrity` works.** `ratings_in_range`
  referenced nonexistent columns (`shooting/skating/defense/physicality`); it now
  checks real rating columns.
- **`sync` drops duplicate `card_id`s** (the site occasionally serves a card on
  two pages), keeping `(snapshot_date, card_id)` unique.

## 0.1.0

Initial release.

- `sync` command writes a dated snapshot to `hut_player_ratings`
- Snapshot-typed (no `--chunk-by`); re-running same `--snapshot-date` is idempotent
- 5 doc renderers (bq-apply / llm / dictionary / markdown / dbt) backed by ColumnSpec SSoT
- `verify --aggregation snapshot-integrity` runs zero-tolerance internal checks
- `verify --aggregation cross-snapshot-drift` flags suspicious rating changes
- `resolve-ids` command builds `hut_player_xref` via 4-rung match ladder against `nhl-bigquery`'s `boxscore_stats`
- `verify --aggregation hut-coverage` reports `pct_nhl_minutes` headline coverage metric
- Trip-wires on degenerate scrape payloads (< 50 or > 50,000 cards)
