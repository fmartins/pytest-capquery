import pytest
from pytest_capquery.plugin import reformat_query


def test_reformat_query_multiple_queries():
    with pytest.raises(ValueError, match="Only one query is allowed."):
        reformat_query("SELECT 1; SELECT 2;")


def test_reformat_query_empty_string():
    assert reformat_query("") == ""
    assert reformat_query("   ") == ""
    assert reformat_query("\n\t") == ""
