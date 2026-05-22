# Changelog

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
