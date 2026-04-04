"""
Validation of the core event execution matching and transaction boundaries.

This module rigorously proves that the underlying assertion components correctly
trap mismatches across statement quantities, executed query formatting, parameters,
and complex nested transactional savepoints cleanly utilizing the SQLite driver.
"""
import pytest
from sqlalchemy import create_engine, text

from pytest_capquery.models import TxEvent
from pytest_capquery.plugin import CapQueryWrapper
from pytest_capquery.snapshot import SnapshotManager


def test_single_query(capquery, sqlite_engine):
    """
    Validates that a singular executed query is successfully verified, correctly
    identified within its ambient transaction boundary lifecycle tracking.
    """
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT :x"), {"x": 1})

    capquery.assert_executed_queries(
        "BEGIN",
        ("SELECT ?", (1,)),
        "ROLLBACK"
    )


def test_multiple_queries(capquery, sqlite_engine):
    """
    Validates that multiple linearly executed queries successfully form
    chronological ordered sequences verifiable under the assertion framework.
    """
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT 2"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SELECT 2",
        "ROLLBACK"
    )


def test_commit(capquery, sqlite_engine):
    """
    Confirms an explicit commit lifecycle generates matching BEGIN and COMMIT
    events alongside correctly registered nested SAVEPOINT interactions.
    """
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested():
                conn.execute(text("SELECT 2"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "RELEASE SAVEPOINT sa_savepoint_1",
        "COMMIT"
    )


def test_nested_transaction_rollback(capquery, sqlite_engine):
    """
    Confirms nested transaction rollback behavior suppresses standard RELEASE
    markers and legitimately emits ROLLBACK TO SAVEPOINT signals perfectly matching runtime.
    """
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 2"))
                nested.rollback()

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "ROLLBACK TO SAVEPOINT sa_savepoint_1",
        "COMMIT"
    )


def test_complex_nested_transactions(capquery, sqlite_engine):
    """
    Proves comprehensive multi-layered deeply nested executions including successful
    releases alongside rolling back targeted sub-phases resolve meticulously.
    """
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested():
                conn.execute(text("SELECT 2"))

            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 3"))
                nested.rollback()

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "RELEASE SAVEPOINT sa_savepoint_1",
        "SAVEPOINT sa_savepoint_2",
        "SELECT 3",
        "ROLLBACK TO SAVEPOINT sa_savepoint_2",
        "COMMIT"
    )


def test_transaction_begin_commit(capquery, sqlite_engine):
    """
    Ensures baseline engine context manager invocations yield standard simple
    commit boundaries appropriately.
    """
    with sqlite_engine.begin() as conn:
        conn.execute(text("SELECT 1"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "COMMIT"
    )


def test_transaction_rollback(capquery, sqlite_engine):
    """
    Ensures manual connection closures following specific execution rollback loops
    are mapped reliably without hanging connections.
    """
    conn = sqlite_engine.connect()
    trans = conn.begin()
    conn.execute(text("SELECT 1"))
    trans.rollback()
    conn.close()

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "ROLLBACK"
    )


def test_nested_partial_rollback(capquery, sqlite_engine):
    """
    Verifies that subsequent statements seamlessly append into the global transaction
    chain post-recovery of a nested sub-transaction rollback.
    """
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 2"))
                nested.rollback()
            conn.execute(text("SELECT 3"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "ROLLBACK TO SAVEPOINT sa_savepoint_1",
        "SELECT 3",
        "COMMIT"
    )


def test_assertion_error_count_mismatch(capquery, sqlite_engine):
    """
    Ensures the assertion engine correctly flags a mismatch in the raw chronological
    length of executed tuples compared to expectations.
    """
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
    """
    Guarantees structural variance in SQL statement sequences triggers precise and
    actionably diffed validation error blocks exposing actual against expected outputs.
    """
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
    """
    Identifies bounds parameter failures dynamically, providing a strict failure
    should actual execution bound variables misalign with their hardcoded specification.
    """
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
    """
    Provides developer coverage warning if a developer explicitly asserts an empty
    parameter signature but underlying SQL triggers runtime injections anyway.
    """
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
    """
    Verifies timeline overrun expectations correctly fail when developers declare more
    testing conditions than actual timeline triggers resolve during assertion sequence.
    """
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
    Validates that a failed assertion outputs a strictly and perfectly formatted
    Python block to standard out facilitating rapid copy-pasting for regression fixes.
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


def test_assertion_error_copy_paste_block_no_params(capquery, capsys):
    """
    Ensures robust generation parameter combinations are handled seamlessly
    for the terminal output block ensuring deep coverage logic triggers nicely.
    """
    capquery.statements.append(TxEvent("BEGIN"))

    long_sql = "SELECT column_a, column_b, column_c FROM some_very_long_table_name"
    capquery.statements.append(TxEvent(statement=long_sql, parameters=None))

    with pytest.raises(AssertionError):
        capquery.assert_executed_queries("EXPECTED_SOMETHING_ELSE")

    stdout = capsys.readouterr().out

    assert '    "BEGIN"' in stdout
    assert "FROM some_very_long_table_name" in stdout


def test_assertion_error_copy_paste_block_empty_query(capquery, capsys):
    """
    Ensures complete formatting stability preventing unexpected terminal panics
    if capturing perfectly empty queries internally.
    """
    empty_stmt = TxEvent(statement="", parameters=None)
    capquery.statements.append(empty_stmt)

    with pytest.raises(AssertionError):
        capquery.assert_executed_queries("EXPECTED_SOMETHING_ELSE")

    stdout = capsys.readouterr().out

    assert "assert_executed_queries(\n\n)" in stdout


def test_assert_matches_snapshot_without_manager():
    engine = create_engine("sqlite:///:memory:")
    wrapper = CapQueryWrapper(engine)
    context = wrapper.capture()
    with pytest.raises(RuntimeError, match="SnapshotManager is not configured. Ensure capquery fixture is used correctly."):
        context.assert_matches_snapshot()


def test_assert_matches_snapshot_exceeds_phases(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    snapshot_manager = SnapshotManager(
        nodeid="test",
        test_path=tmp_path / "test.py",
        update_mode=False
    )
    snapshot_manager.snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_manager.snapshot_file.write_text(
        "-- CAPQUERY: Query 1\n"
        "-- EXPECTED_PARAMS: None\n"
        "-- PHASE: 1\n"
        "SELECT 1\n"
    )

    wrapper = CapQueryWrapper(engine, snapshot_manager=snapshot_manager)

    with wrapper.capture(assert_snapshot=True):
        wrapper.statements.append(TxEvent(statement="SELECT 1"))

    with pytest.raises(AssertionError, match="Snapshot missing phase 2"):
        with wrapper.capture(assert_snapshot=True):
            pass
