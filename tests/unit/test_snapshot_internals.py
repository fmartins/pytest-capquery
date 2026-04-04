import pytest
from sqlalchemy import text

from pytest_capquery.plugin import CapQueryWrapper, SnapshotManager


def test_internal_catching_a_sql_regression(sqlite_engine, db_session, tmp_path):
    """
    INTERNAL: Verifies that a mismatch between the execution timeline and
    the loaded .sql snapshot correctly raises an AssertionError with a diff.
    """
    test_file = tmp_path / "test_regression.py"

    sm_update = SnapshotManager(nodeid="test_regression", test_path=test_file, update_mode=True)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_update) as wrapper_update:
        with wrapper_update.capture() as phase:
            db_session.execute(text("SELECT 1"))
        phase.assert_matches_snapshot()

    # Reset the session transaction state so the next capture records a fresh BEGIN event
    db_session.rollback()

    sm_read = SnapshotManager(nodeid="test_regression", test_path=test_file, update_mode=False)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_read) as wrapper_read:
        with wrapper_read.capture() as regression_phase:
            db_session.execute(text("SELECT 2"))

        with pytest.raises(AssertionError) as exc_info:
            regression_phase.assert_matches_snapshot()

    error_msg = str(exc_info.value)
    # Index 0 is the BEGIN transaction event, Index 1 is the actual SELECT query
    assert "Mismatch at index 1" in error_msg
    assert "Expected SQL:\nSELECT 1" in error_msg
    assert "Actual SQL:\nSELECT 2" in error_msg


def test_internal_missing_snapshot_file(sqlite_engine, db_session, tmp_path):
    """
    INTERNAL: Ensures the plugin provides helpful instructions if a developer
    calls `assert_matches_snapshot()` before generating the file.
    """
    test_file = tmp_path / "test_missing.py"

    sm_read = SnapshotManager(nodeid="test_missing", test_path=test_file, update_mode=False)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_read) as wrapper_read:
        with wrapper_read.capture() as phase:
            db_session.execute(text("SELECT 1"))

        with pytest.raises(AssertionError) as exc_info:
            phase.assert_matches_snapshot()

    error_msg = str(exc_info.value)
    assert "No snapshot found for this test." in error_msg
    assert "Run pytest with `--capquery-update` to generate it" in error_msg


def test_internal_snapshot_file_overwritten_in_update_mode(sqlite_engine, db_session, tmp_path):
    """
    INTERNAL: Ensures that running in update_mode actively overwrites
    an existing snapshot file rather than appending or failing.
    """
    test_file = tmp_path / "test_overwrite.py"

    sm_update1 = SnapshotManager(nodeid="test_overwrite", test_path=test_file, update_mode=True)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_update1) as wrapper_update1:
        with wrapper_update1.capture() as phase1:
            db_session.execute(text("SELECT 'OLD'"))
        phase1.assert_matches_snapshot()

    # Reset the session transaction state
    db_session.rollback()

    sm_update2 = SnapshotManager(nodeid="test_overwrite", test_path=test_file, update_mode=True)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_update2) as wrapper_update2:
        with wrapper_update2.capture() as phase2:
            db_session.execute(text("SELECT 'NEW'"))
        phase2.assert_matches_snapshot()

    content = sm_update2.snapshot_file.read_text()
    assert "SELECT 'NEW'" in content
    assert "SELECT 'OLD'" not in content
