import pytest

from nhl_hut_bigquery.parser import check_payload_size


def test_too_few_cards_raises():
    with pytest.raises(ValueError, match="too few"):
        check_payload_size(card_count=30, min_expected=50, max_expected=50_000)


def test_too_many_cards_raises():
    with pytest.raises(ValueError, match="too many"):
        check_payload_size(card_count=100_000, min_expected=50, max_expected=50_000)


def test_in_range_passes():
    check_payload_size(card_count=5000, min_expected=50, max_expected=50_000)
