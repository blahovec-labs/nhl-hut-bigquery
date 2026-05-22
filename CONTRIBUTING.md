# Contributing

Bug reports and PRs welcome at https://github.com/blahovec-labs/nhl-hut-bigquery.

## Dev setup

    pip install -e ".[dev]"
    pytest -q

## Reconnaissance step

Before adding or changing scraper/parser code, run the reconnaissance script to confirm the current endpoint shape:

    python scripts/inspect_current_site.py --start 0 --length 5

Document any endpoint changes in `docs/current_endpoint.md`.

## Capturing test fixtures

    python scripts/capture_fixture.py --out tests/fixtures/hut/
