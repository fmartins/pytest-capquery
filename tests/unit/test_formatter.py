"""Validation of SQL query formatting and normalization logic.

This module rigorously tests the behavior of the `reformat_query` utility,
ensuring it accurately standardizes SQL commands, strips extraneous whitespace,
and catches invalid inputs, establishing a reliable bedrock for execution timeline assertions.
Additionally, it validates the determinism of parameter normalization functions.
"""

import pytest
from pytest_capquery.formatter import normalize_params, reformat_query


def test_reformat_query_multiple_queries():
    """Ensure the formatter correctly identifies and rejects attempts to process multiple queries
    concatenated into a single execution statement, enforcing transactional atomicity."""
    with pytest.raises(ValueError, match="Only one query is allowed."):
        reformat_query("SELECT 1; SELECT 2;")


def test_reformat_query_empty_string():
    """Ensure the formatter gracefully manages completely empty or whitespace-only strings,
    resolving them strictly to an empty representation rather than failing."""
    assert reformat_query("") == ""
    assert reformat_query("   ") == ""
    assert reformat_query("\n\t") == ""


def test_reformat_query_happy_path():
    """Verify the formatter successfully applies syntactical capitalizations, newline integrations,
    and whitespace homogenizations on standard raw SQL statements."""
    raw_sql = "select id, name from users where status='active'"
    formatted = reformat_query(raw_sql)

    assert "SELECT" in formatted
    assert "FROM" in formatted
    assert "WHERE" in formatted
    assert "\n" in formatted


def test_normalize_params_dictionary_sorting():
    """Validate that dictionary parameters are converted robustly into tuples of tuples, sorted
    strictly by their keys, thereby guaranteeing assertion equality across test runs regardless of
    randomized dictionary insertion ordering."""
    params1 = {"b": 2, "a": 1}
    params2 = {"a": 1, "b": 2}

    norm1 = normalize_params(params1)
    norm2 = normalize_params(params2)

    assert norm1 == (("a", 1), ("b", 2))
    assert norm1 == norm2


def test_normalize_params_list_and_tuple_conversion():
    """Guarantee that deeply nested list and dictionary configurations are comprehensively mapped to
    immutable tuples spanning their entirety recursively."""
    params = [1, {"z": 26, "y": 25}, [3, 4]]
    expected = (1, (("y", 25), ("z", 26)), (3, 4))

    assert normalize_params(params) == expected


def test_normalize_params_scalars():
    """Certify that base primitive types trivially navigate through normalization logic without
    unwanted boxing or structural modifications."""
    assert normalize_params(1) == 1
    assert normalize_params("string") == "string"
    assert normalize_params(None) is None
