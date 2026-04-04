"""Snapshot assertion validation tests for the SQLite dialect.

This module replicates the precise database interactions evaluated in the explicit execution tests,
but enforces the automated snapshotting feature instead. This ensures parity between explicit string
assertions and transparent disk-based snapshot assertions.
"""

from sqlalchemy.orm import joinedload

from tests.models import AlarmPanel, Sensor


def test_insert_and_select_snapshot(sqlite_session, sqlite_capquery):
    """Validate that SQLite insert and complex select operations emit the correct chronological
    events which are accurately captured and automatically evaluated against the disk file by the
    snapshot assertion system.

    Snapshot Asset: `__capquery_snapshots__/test_snapshot/test_insert_and_select_snapshot.sql`
    """
    with sqlite_capquery.capture(assert_snapshot=True):
        panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
        sensor = Sensor(name="Front Door", sensor_type="Contact")
        panel.sensors.append(sensor)

        sqlite_session.add(panel)
        sqlite_session.flush()

        queried_panel = (
            sqlite_session.query(AlarmPanel)
            .options(joinedload(AlarmPanel.sensors))
            .filter_by(mac_address="00:11:22:33:44:55")
            .first()
        )
        assert queried_panel is not None
