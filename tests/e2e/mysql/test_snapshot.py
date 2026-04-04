"""Snapshot assertion validation tests for the MySQL dialect.

This module replicates the precise database interactions evaluated in the explicit execution tests,
but enforces the automated snapshotting feature instead. This ensures parity between explicit string
assertions and transparent disk-based snapshot assertions.
"""

import pytest
from sqlalchemy.orm import joinedload

from tests.models import AlarmPanel, Sensor

pytestmark = pytest.mark.xdist_group("e2e_mysql")


def test_insert_and_select_snapshot(mysql_session, mysql_capquery):
    """Validate that MySQL inserts and complex select operations emit the expected events which are
    accurately captured and automatically evaluated against the disk file by the snapshot assertion
    system.

    Snapshot Asset: `__capquery_snapshots__/test_snapshot/test_insert_and_select_snapshot.sql`
    """
    with mysql_capquery.capture(assert_snapshot=True):
        panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
        sensor = Sensor(name="Front Door", sensor_type="Contact")
        panel.sensors.append(sensor)

        mysql_session.add(panel)
        mysql_session.flush()

        queried_panel = (
            mysql_session.query(AlarmPanel)
            .options(joinedload(AlarmPanel.sensors))
            .filter_by(mac_address="00:11:22:33:44:55")
            .first()
        )
        assert queried_panel is not None
