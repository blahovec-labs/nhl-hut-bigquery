from nhl_hut_bigquery.schema import HUT_RATINGS_SCHEMA, get_partitioning

TABLES = {
    "hut_player_ratings": {
        "schema": HUT_RATINGS_SCHEMA,
        "partitioning": get_partitioning(),
    },
}
