import pytest
from sqlalchemy import text


def test_internal_catching_a_sql_regression(sqlite_engine, capquery, tmp_path):
    """
    INTERNAL: Verifies that a mismatch between the execution timeline and
    the loaded .sql snapshot correctly raises an AssertionError with a diff.
    """
    capquery.snapshot_manager.snapshot_dir = tmp_path
    capquery.snapshot_manager.snapshot_file = tmp_path / "regression.sql"

    # 1. Manually force the plugin into update mode to generate the baseline
    capquery.snapshot_manager.update_mode = True
    with sqlite_engine.begin() as conn:
        with capquery.capture() as phase:
            conn.execute(text("SELECT 1"))
        phase.assert_matches_snapshot()

    # 2. Reset the timeline and force it back into read mode
    capquery.snapshot_manager.update_mode = False
    capquery.statements.clear()

    # 3. Simulate a regression (changed query footprint)
    with sqlite_engine.begin() as conn:
        with capquery.capture() as regression_phase:
            conn.execute(text("SELECT 2"))

        # The assertion should catch the difference
        with pytest.raises(AssertionError) as exc_info:
            regression_phase.assert_matches_snapshot()

    error_msg = str(exc_info.value)
    assert "Mismatch at index 0" in error_msg
    assert "Expected SQL:\nSELECT 1" in error_msg
    assert "Actual SQL:\nSELECT 2" in error_msg


def test_internal_missing_snapshot_file(sqlite_engine, capquery, tmp_path):
    """
    INTERNAL: Ensures the plugin provides helpful instructions if a developer
    calls `assert_matches_snapshot()` before generating the file.
    """
    capquery.snapshot_manager.snapshot_file = tmp_path / "does_not_exist.sql"
    capquery.snapshot_manager.update_mode = False

    with sqlite_engine.begin() as conn:
        with capquery.capture() as phase:
            conn.execute(text("SELECT 1"))

        with pytest.raises(AssertionError) as exc_info:
            phase.assert_matches_snapshot()

    error_msg = str(exc_info.value)
    assert "No snapshot found for this test." in error_msg
    assert "Run pytest with `--capquery-update` to generate it" in error_msg


def test_internal_snapshot_file_overwritten_in_update_mode(sqlite_engine, capquery, tmp_path):
    """
    INTERNAL: Ensures that running in update_mode actively overwrites
    an existing snapshot file rather than appending or failing.
    """
    capquery.snapshot_manager.snapshot_dir = tmp_path
    capquery.snapshot_manager.snapshot_file = tmp_path / "overwrite.sql"

    # Create an initial file
    capquery.snapshot_manager.update_mode = True
    with sqlite_engine.begin() as conn:
        with capquery.capture() as phase1:
            conn.execute(text("SELECT 'OLD'"))
        phase1.assert_matches_snapshot()

    # Run update_mode again with new data
    capquery.statements.clear()
    with sqlite_engine.begin() as conn:
        with capquery.capture() as phase2:
            conn.execute(text("SELECT 'NEW'"))
        phase2.assert_matches_snapshot()

    # Verify the file was overwritten, not appended
    content = capquery.snapshot_manager.snapshot_file.read_text()
    assert "SELECT 'NEW'" in content
    assert "SELECT 'OLD'" not in content
