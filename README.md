# nhl-hut-bigquery

EA NHL Ultimate Team player ratings → BigQuery snapshots, with cross-source resolver to `nhl-bigquery`.

## Install

    pip install nhl-hut-bigquery

## Quickstart

    gcloud auth application-default login
    nhl-hut-bigquery sync --table myproject.mydataset.hut_player_ratings

Companion to [`nhl-bigquery`](https://pypi.org/project/nhl-bigquery/) — install both for the cross-source resolver and coverage metrics.

MIT licensed. This software does not include or distribute EA-owned data.
