"""Validation of the primary Pytest CapQuery plugin interface mechanisms.

This module guarantees that the context encapsulation layer works reliably to isolate tracked
database events securely without leaking transactional scope parameters globally.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from pytest_capquery.models import TxEvent
from pytest_capquery.plugin import CapQueryWrapper


def test_capture_block_isolation(sqlite_engine, sqlite_capquery):
    """Ensures that queries executed outside the specific capture context block are not visible
    inside its internal ledger, but the parent global wrapper maintains omnipresent scope
    tracking."""
    with sqlite_engine.begin() as conn:
        conn.execute(text("SELECT 1"))

        with sqlite_capquery.capture() as phase:
            conn.execute(text("SELECT 2"))
            conn.execute(text("SELECT 3"))

        conn.execute(text("SELECT 4"))

    phase.assert_executed_queries("SELECT 2", "SELECT 3", strict=True)

    sqlite_capquery.assert_executed_queries(
        "BEGIN", "SELECT 1", "SELECT 2", "SELECT 3", "SELECT 4", "COMMIT", strict=True
    )


def test_multiple_sequential_captures(sqlite_engine, sqlite_capquery):
    """Verifies that declaring sequence-based parallel capture boundaries safely establishes strict
    chronological segmentation logic across all involved instances reliably."""
    with sqlite_engine.begin() as conn:
        with sqlite_capquery.capture() as phase_one:
            conn.execute(text("SELECT 'A'"))

        with sqlite_capquery.capture() as phase_two:
            conn.execute(text("SELECT 'B'"))
            conn.execute(text("SELECT 'C'"))

    phase_one.assert_executed_queries("SELECT 'A'")
    phase_two.assert_executed_queries("SELECT 'B'", "SELECT 'C'")

    sqlite_capquery.assert_executed_queries(
        "BEGIN", "SELECT 'A'", "SELECT 'B'", "SELECT 'C'", "COMMIT"
    )


def test_capture_expected_count_success(sqlite_engine, sqlite_capquery):
    """Validates that the expected statement quantity constraints silently yield correctly when
    boundary lengths align structurally to the strict metric assigned directly."""
    with sqlite_engine.begin() as conn:
        with sqlite_capquery.capture(expected_count=2):
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT 2"))


def test_capture_expected_count_failure(sqlite_engine, sqlite_capquery):
    """Establishes that exceeding execution limits promptly evaluates the block termination logic
    yielding critical validation exception sequences dynamically notifying the layer."""
    with sqlite_engine.begin() as conn:
        with pytest.raises(AssertionError, match="Expected 1 queries, but found 2"):
            with sqlite_capquery.capture(expected_count=1):
                conn.execute(text("SELECT 1"))
                conn.execute(text("SELECT 2"))


def test_capture_expected_count_bypassed_on_exception(sqlite_engine, sqlite_capquery):
    """Protects user experience ensuring unexpected business logic framework crashes bypass the
    secondary assertions internally preserving parent traceability stack tracks natively."""

    class BusinessLogicError(Exception):
        pass

    with pytest.raises(BusinessLogicError):
        with sqlite_engine.begin() as conn:
            with sqlite_capquery.capture(expected_count=2):
                conn.execute(text("SELECT 1"))
                raise BusinessLogicError("Something went wrong in the app")


def test_capture_active_state_assertions(sqlite_engine, sqlite_capquery):
    """Asserts validation handlers successfully maintain execution verification capabilities while
    running functionally mid-transaction continuously across the scope stack directly."""
    with sqlite_engine.begin() as conn:
        with sqlite_capquery.capture() as active_phase:
            conn.execute(text("SELECT 1"))

            active_phase.assert_executed_queries("SELECT 1")

            conn.execute(text("SELECT 2"))

            active_phase.assert_executed_queries("SELECT 1", "SELECT 2")


def test_wrapper_exit_closes_resources():
    """Confirms that resource closure pathways traverse mock connection states safely during exit
    sequences."""
    engine = create_engine("sqlite:///:memory:")

    wrapper = CapQueryWrapper(engine)
    wrapper.__enter__()

    real_cur = wrapper._cur
    real_conn = wrapper.connection

    mock_cur = MagicMock()
    mock_conn = MagicMock()
    wrapper._cur = mock_cur
    wrapper.connection = mock_conn

    wrapper.__exit__(None, None, None)

    mock_cur.close.assert_called_once()
    mock_conn.close.assert_called_once()

    if real_cur:
        real_cur.close()
    if real_conn:
        real_conn.close()

    wrapper2 = CapQueryWrapper(engine)
    wrapper2.__enter__()

    real_cur2 = wrapper2._cur
    real_conn2 = wrapper2.connection

    mock_cur_exception = MagicMock()
    mock_cur_exception.close.side_effect = Exception()
    mock_conn_exception = MagicMock()
    mock_conn_exception.close.side_effect = Exception()

    wrapper2._cur = mock_cur_exception
    wrapper2.connection = mock_conn_exception
    wrapper2.__exit__(None, None, None)

    if real_cur2:
        real_cur2.close()
    if real_conn2:
        real_conn2.close()

    engine.dispose()


def test_serialize_snapshot_ignores_empty_query():
    """Validates that attempting to serialize structurally empty event statements correctly omits
    them entirely from file outputs gracefully."""
    engine = create_engine("sqlite:///:memory:")
    wrapper = CapQueryWrapper(engine)
    wrapper.statements.append(TxEvent(statement=""))
    wrapper.phases.append({"alias": None, "statements": wrapper.statements})

    result = wrapper._serialize_snapshot()

    assert result == "\n"

    engine.dispose()


def test_deserialize_snapshot_ignores_empty_query():
    """Ensures that snapshot parsing handles empty bounds properly and reverses formatting logic
    back into clean object representations correctly."""
    engine = create_engine("sqlite:///:memory:")
    wrapper = CapQueryWrapper(engine)
    content = "-- CAPQUERY: Query 1\n-- EXPECTED_PARAMS: None\n-- PHASE: 1\n"

    result = wrapper._deserialize_snapshot(content)

    assert result == []

    engine.dispose()
