import pytest
from pytest_capquery.formatter import normalize_params, reformat_query


def test_reformat_query_multiple_queries():
    with pytest.raises(ValueError, match="Only one query is allowed."):
        reformat_query("SELECT 1; SELECT 2;")


def test_reformat_query_empty_string():
    assert reformat_query("") == ""
    assert reformat_query("   ") == ""
    assert reformat_query("\n\t") == ""


def test_reformat_query_happy_path():
    raw_sql = "select id, name from users where status='active'"
    formatted = reformat_query(raw_sql)

    # sqlparse with keyword_case="upper" and reindent=True should capitalize and wrap lines
    assert "SELECT" in formatted
    assert "FROM" in formatted
    assert "WHERE" in formatted
    assert "\n" in formatted


def test_normalize_params_dictionary_sorting():
    """
    Ensures dictionaries are converted to tuples of tuples sorted strictly by key.
    This guarantees equality across runs regardless of dictionary insertion order.
    """
    params1 = {"b": 2, "a": 1}
    params2 = {"a": 1, "b": 2}

    norm1 = normalize_params(params1)
    norm2 = normalize_params(params2)

    assert norm1 == (("a", 1), ("b", 2))
    assert norm1 == norm2


def test_normalize_params_list_and_tuple_conversion():
    """
    Ensures lists and nested structures are recursively converted into immutable tuples.
    """
    params = [1, {"z": 26, "y": 25}, [3, 4]]
    expected = (1, (("y", 25), ("z", 26)), (3, 4))

    assert normalize_params(params) == expected


def test_normalize_params_scalars():
    """
    Ensures primitive types pass through normalization completely unchanged.
    """
    assert normalize_params(1) == 1
    assert normalize_params("string") == "string"
    assert normalize_params(None) is None
