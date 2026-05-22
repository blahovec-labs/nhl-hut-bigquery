# nhl-hut-bigquery

EA NHL Ultimate Team player ratings → BigQuery snapshots, with cross-source resolver and coverage metrics linking HUT cards to NHL stats.

## Install

    pip install nhl-hut-bigquery

This package is a sibling to [`nhl-bigquery`](https://pypi.org/project/nhl-bigquery/). Install both for the full experience:

    pip install nhl-bigquery nhl-hut-bigquery

## Quickstart

    gcloud auth application-default login

    # 1. Snapshot today's HUT ratings
    nhl-hut-bigquery sync \
        --table myproject.mydataset.hut_player_ratings

    # 2. Resolve HUT cards to NHL player_ids (requires nhl-bigquery's boxscore_stats)
    nhl-hut-bigquery resolve-ids \
        --xref-table myproject.mydataset.hut_player_xref \
        --hut-table myproject.mydataset.hut_player_ratings \
        --nhl-boxscore-table myproject.mydataset.boxscore_stats \
        --season 2024

    # 3. How much of NHL ice-time is covered by today's HUT snapshot?
    nhl-hut-bigquery verify \
        --aggregation hut-coverage \
        --xref-table myproject.mydataset.hut_player_xref \
        --nhl-boxscore-table myproject.mydataset.boxscore_stats \
        --season 2024 --snapshot-date 2026-05-22

## Documentation

    nhl-hut-bigquery docs --format llm > HUT_FOR_LLMS.md
    nhl-hut-bigquery docs --format markdown > schema.md

## Verification

    # Internal integrity checks on a snapshot (overall in range, no dupes, …)
    nhl-hut-bigquery verify --aggregation snapshot-integrity \
        --table myproject.mydataset.hut_player_ratings

    # Drift checks between consecutive snapshots
    nhl-hut-bigquery verify --aggregation cross-snapshot-drift \
        --table myproject.mydataset.hut_player_ratings

MIT licensed. This software does not include or distribute EA-owned data.
