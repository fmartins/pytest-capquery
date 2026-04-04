import pytest
from sqlalchemy import text


def test_assertion_error_count_mismatch(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT 2"))

    with pytest.raises(AssertionError, match=r"Expected 3 queries, but found 4\."):
        capquery.assert_executed_queries(
            "BEGIN",
            "SELECT 1",
            "ROLLBACK"
        )


def test_assertion_error_sql_mismatch(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    with pytest.raises(AssertionError) as exc_info:
        capquery.assert_executed_queries(
            "BEGIN",
            "SELECT 2",
            "ROLLBACK"
        )

    error_msg = str(exc_info.value)
    assert "Expected SQL:" in error_msg
    assert "Actual SQL:" in error_msg
    assert "SELECT 2" in error_msg
    assert "SELECT 1" in error_msg


def test_assertion_error_parameter_mismatch(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT :x"), {"x": 1})

    with pytest.raises(AssertionError) as exc_info:
        capquery.assert_executed_queries(
            "BEGIN",
            ("SELECT ?", (2,)),
            "ROLLBACK"
        )

    error_msg = str(exc_info.value)
    assert "Expected Params:" in error_msg
    assert "Actual Params:" in error_msg


def test_assertion_error_unexpected_parameters(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT :x"), {"x": 1})

    with pytest.raises(AssertionError) as exc_info:
        capquery.assert_executed_queries(
            "BEGIN",
            "SELECT ?",
            "ROLLBACK"
        )

    error_msg = str(exc_info.value)
    assert "Expected Params to be empty or None, but got:" in error_msg


def test_assertion_error_missing_executed_query(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    with pytest.raises(AssertionError) as exc_info:
        capquery.assert_executed_queries(
            "BEGIN",
            "SELECT 1",
            "ROLLBACK",
            "SELECT 2",
            strict=False
        )

    error_msg = str(exc_info.value)
    assert "Mismatch at index 3" in error_msg
    assert "Expected query or event but no more statements were recorded" in error_msg


def test_assertion_error_generates_stdout_copy_paste_block(capquery, sqlite_engine, capsys):
    """
    Validates that a failed assertion outputs the perfectly formatted
    Python block to sys.stdout for easy copy-pasting.
    """
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    with pytest.raises(AssertionError):
        capquery.assert_executed_queries(
            "BEGIN",
            "SELECT 2",
            "ROLLBACK"
        )

    captured = capsys.readouterr()
    stdout = captured.out

    expected_stdout = (
        "\n"
        "================================================================================\n"
        "🚨 CAPQUERY: COPY & PASTE TO FIX ASSERTION 🚨\n"
        "================================================================================\n"
        "\n"
        "assert_executed_queries(\n"
        '    "BEGIN",\n'
        "    (\n"
        "        # language=SQL\n"
        '        """\n'
        "        SELECT 1\n"
        '        """,\n'
        "        ()\n"
        "    ),\n"
        '    "ROLLBACK"\n'
        ")\n"
        "\n"
        "================================================================================\n"
    )

    assert stdout == expected_stdout
