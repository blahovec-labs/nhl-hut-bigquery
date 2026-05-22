"""nhl-hut-bigquery: EA NHL HUT player ratings → BigQuery snapshots.

Provides a CLI and library for scraping EA NHL Ultimate Team player ratings
from nhlhutbuilder.com and writing daily snapshots into BigQuery. Includes a
cross-source resolver that matches HUT cards to NHL player IDs from
nhl-bigquery's boxscore_stats table, and a hut-coverage verifier that reports
what fraction of NHL minutes played is covered by each HUT snapshot per season.
"""

from nhl_hut_bigquery._version import __version__

__all__ = ["__version__"]
