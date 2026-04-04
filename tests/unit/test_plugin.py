"""
Validation of the primary Pytest CapQuery plugin interface mechanisms.

This module guarantees that the context encapsulation layer works reliably to isolate
tracked database events securely without leaking transactional scope parameters globally.
"""
import pytest
from sqlalchemy import text


def test_capture_block_isolation(sqlite_engine, capquery):
    """
    Ensures that queries executed outside the specific capture context block are not visible
    inside its internal ledger, but the parent global wrapper maintains omnipresent scope tracking.
    """
    with sqlite_engine.begin() as conn:
        conn.execute(text("SELECT 1"))

        with capquery.capture() as phase:
            conn.execute(text("SELECT 2"))
            conn.execute(text("SELECT 3"))

        conn.execute(text("SELECT 4"))

    phase.assert_executed_queries(
        "SELECT 2",
        "SELECT 3",
        strict=True
    )

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SELECT 2",
        "SELECT 3",
        "SELECT 4",
        "COMMIT",
        strict=True
    )


def test_multiple_sequential_captures(sqlite_engine, capquery):
    """
    Verifies that declaring sequence-based parallel capture boundaries safely establishes
    strict chronological segmentation logic across all involved instances reliably.
    """
    with sqlite_engine.begin() as conn:
        with capquery.capture() as phase_one:
            conn.execute(text("SELECT 'A'"))

        with capquery.capture() as phase_two:
            conn.execute(text("SELECT 'B'"))
            conn.execute(text("SELECT 'C'"))

    phase_one.assert_executed_queries("SELECT 'A'")
    phase_two.assert_executed_queries("SELECT 'B'", "SELECT 'C'")

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 'A'",
        "SELECT 'B'",
        "SELECT 'C'",
        "COMMIT"
    )


def test_capture_expected_count_success(sqlite_engine, capquery):
    """
    Validates that the expected statement quantity constraints silently yield correctly
    when boundary lengths align structurally to the strict metric assigned directly.
    """
    with sqlite_engine.begin() as conn:
        with capquery.capture(expected_count=2):
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT 2"))


def test_capture_expected_count_failure(sqlite_engine, capquery):
    """
    Establishes that exceeding execution limits promptly evaluates the block termination
    logic yielding critical validation exception sequences dynamically notifying the layer.
    """
    with sqlite_engine.begin() as conn:
        with pytest.raises(AssertionError, match="Expected 1 queries, but found 2"):
            with capquery.capture(expected_count=1):
                conn.execute(text("SELECT 1"))
                conn.execute(text("SELECT 2"))


def test_capture_expected_count_bypassed_on_exception(sqlite_engine, capquery):
    """
    Protects user experience ensuring unexpected business logic framework crashes bypass
    the secondary assertions internally preserving parent traceability stack tracks natively.
    """

    class BusinessLogicError(Exception):
        pass

    with pytest.raises(BusinessLogicError):
        with sqlite_engine.begin() as conn:
            with capquery.capture(expected_count=2):
                conn.execute(text("SELECT 1"))
                raise BusinessLogicError("Something went wrong in the app")


def test_capture_active_state_assertions(sqlite_engine, capquery):
    """
    Asserts validation handlers successfully maintain execution verification capabilities
    while running functionally mid-transaction continuously across the scope stack directly.
    """
    with sqlite_engine.begin() as conn:
        with capquery.capture() as active_phase:
            conn.execute(text("SELECT 1"))

            active_phase.assert_executed_queries("SELECT 1")

            conn.execute(text("SELECT 2"))

            active_phase.assert_executed_queries("SELECT 1", "SELECT 2")
