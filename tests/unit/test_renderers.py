from nhl_hut_bigquery.docs.renderers import (
    render_bq_descriptions, render_dbt_yaml,
    render_llm_context, render_markdown,
)


def test_llm_includes_hut_table():
    out = render_llm_context()
    assert "hut_player_ratings" in out
    assert "overall" in out


def test_markdown_non_empty():
    assert len(render_markdown().strip()) > 100


def test_dbt_yaml():
    assert render_dbt_yaml().startswith("version: 2")


def test_bq_descriptions():
    fields = render_bq_descriptions(table_kind="hut_player_ratings")
    assert len(fields) > 0
