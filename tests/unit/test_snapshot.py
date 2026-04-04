"""
Validation of the Snapshot capture generation and assertion capabilities.

This module guarantees comprehensive testing of the physical disk verification paths,
confirming automated query comparison handles updating sequences securely while failing
dynamically when runtime timeline representations drift from established persistence logic.
"""
import pytest
from sqlalchemy import text

from pytest_capquery.plugin import CapQueryWrapper
from pytest_capquery.snapshot import SnapshotManager
from tests.models import AlarmPanel, Sensor


def test_user_business_logic(db_session, capquery):
    """
    Simulates a standard practical snapshot generation sequence, verifying the
    plugin captures local nested blocks directly resolving them appropriately against
    implicit automated file allocations automatically tied to the host test invocation.
    """
    panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
    db_session.add(panel)
    db_session.flush()

    with capquery.capture(assert_snapshot=True):
        sensor = Sensor(name="Front Door", sensor_type="Contact")
        panel.sensors.append(sensor)
        db_session.flush()


def test_user_multiple_phases(db_session, capquery):
    """
    Confirms multiple capture phases inside single transaction tests write and check
    their relative sequential markers distinctly within the overarching module scope.
    Ensures safe serialization of all phases into a single cohesive snapshot block.
    """
    panel = AlarmPanel(mac_address="AA:BB:CC:DD:EE:FF", is_online=True)

    with capquery.capture(assert_snapshot=True, alias="Panel Setup Phase"):
        db_session.add(panel)
        db_session.flush()

    with capquery.capture(assert_snapshot=True):
        sensor_1 = Sensor(name="Living Room", sensor_type="Motion")
        sensor_2 = Sensor(name="Back Door", sensor_type="Contact")
        panel.sensors.extend([sensor_1, sensor_2])
        db_session.flush()

    with capquery.capture(assert_snapshot=True, alias="Status Toggle and Deletion Phase"):
        panel.is_online = False
        panel.sensors.remove(sensor_1)
        db_session.flush()


def test_internal_catching_a_sql_regression(sqlite_engine, db_session, tmp_path):
    """
    Guarantees logical code drifts trigger accurate output diff comparisons against
    the explicit physical entries ensuring regressions are visibly surfaced quickly.
    """
    test_file = tmp_path / "test_regression.py"

    sm_update = SnapshotManager(nodeid="test_regression", test_path=test_file, update_mode=True)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_update) as wrapper_update:
        with wrapper_update.capture() as phase:
            db_session.execute(text("SELECT 1"))
        phase.assert_matches_snapshot()

    db_session.rollback()

    sm_read = SnapshotManager(nodeid="test_regression", test_path=test_file, update_mode=False)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_read) as wrapper_read:
        with wrapper_read.capture() as regression_phase:
            db_session.execute(text("SELECT 2"))

        with pytest.raises(AssertionError) as exc_info:
            regression_phase.assert_matches_snapshot()

    error_msg = str(exc_info.value)
    assert "Mismatch at index 1" in error_msg
    assert "Expected SQL:\nSELECT 1" in error_msg
    assert "Actual SQL:\nSELECT 2" in error_msg


def test_internal_missing_snapshot_file(sqlite_engine, db_session, tmp_path):
    """
    Proves missing physical representations gracefully surface explicit developer
    instructions guiding them toward generation commands rather than simply failing.
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
    Confirms the pipeline operating in explicit update mode completely replaces
    stale physical markers instead of redundantly appending overlapping execution logic.
    """
    test_file = tmp_path / "test_overwrite.py"

    sm_update1 = SnapshotManager(nodeid="test_overwrite", test_path=test_file, update_mode=True)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_update1) as wrapper_update1:
        with wrapper_update1.capture() as phase1:
            db_session.execute(text("SELECT 'OLD'"))
        phase1.assert_matches_snapshot()

    db_session.rollback()

    sm_update2 = SnapshotManager(nodeid="test_overwrite", test_path=test_file, update_mode=True)
    with CapQueryWrapper(sqlite_engine, snapshot_manager=sm_update2) as wrapper_update2:
        with wrapper_update2.capture() as phase2:
            db_session.execute(text("SELECT 'NEW'"))
        phase2.assert_matches_snapshot()

    content = sm_update2.snapshot_file.read_text()
    assert "SELECT 'NEW'" in content
    assert "SELECT 'OLD'" not in content
