import pytest
from sqlalchemy import text


def test_capture_block_isolation(sqlite_engine, capquery):
    """
    Ensures that queries executed outside the context block are not visible
    to the context manager, but the global wrapper retains everything.
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
    Verifies that multiple sequential capture blocks operate independently
    and do not leak statements into each other.
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
    Validates that the expected_count parameter silently succeeds
    when the exact number of statements is captured.
    """
    with sqlite_engine.begin() as conn:
        with capquery.capture(expected_count=2):
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT 2"))


def test_capture_expected_count_failure(sqlite_engine, capquery):
    """
    Validates that the expected_count parameter raises an AssertionError
    upon exiting the context block if the count misaligns.
    """
    with sqlite_engine.begin() as conn:
        with pytest.raises(AssertionError, match="Expected 1 queries, but found 2"):
            with capquery.capture(expected_count=1):
                conn.execute(text("SELECT 1"))
                conn.execute(text("SELECT 2"))


def test_capture_expected_count_bypassed_on_exception(sqlite_engine, capquery):
    """
    Ensures that if application code raises an exception inside the block,
    the context manager does not swallow it with its own AssertionError.
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
    Ensures that properties and assertions can be called while the context
    manager is still active (inside the block).
    """
    with sqlite_engine.begin() as conn:
        with capquery.capture() as active_phase:
            conn.execute(text("SELECT 1"))

            active_phase.assert_executed_queries("SELECT 1")

            conn.execute(text("SELECT 2"))

            active_phase.assert_executed_queries("SELECT 1", "SELECT 2")
