"""Explicit parameterization validation tests for the SQLite dialect.

This module validates that the assert_executed_queries functionality correctly matches specific,
static SQL strings and their corresponding parameters within an SQLite context, ensuring accurate
transaction event interception.
"""

from sqlalchemy.orm import joinedload

from tests.models import AlarmPanel, Sensor


def test_insert_and_select_normalization(sqlite_session, sqlite_capquery):
    """Validate that SQLite insert and complex joined-load select operations are intercepted and
    accurately matched against explicitly hardcoded query and parameter tuples."""
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

    sqlite_capquery.assert_executed_queries(
        "BEGIN",
        (
            """
            INSERT INTO alarm_panels (mac_address, is_online)
            VALUES (?, ?)
            """,
            ("00:11:22:33:44:55", True),
        ),
        (
            """
            INSERT INTO sensors (panel_id, name, sensor_type)
            VALUES (?, ?, ?)
            """,
            (1, "Front Door", "Contact"),
        ),
        (
            """
            SELECT
                anon_1.alarm_panels_id AS anon_1_alarm_panels_id,
                anon_1.alarm_panels_mac_address AS anon_1_alarm_panels_mac_address,
                anon_1.alarm_panels_is_online AS anon_1_alarm_panels_is_online,
                sensors_1.id AS sensors_1_id,
                sensors_1.panel_id AS sensors_1_panel_id,
                sensors_1.name AS sensors_1_name,
                sensors_1.sensor_type AS sensors_1_sensor_type
            FROM (
                SELECT
                    alarm_panels.id AS alarm_panels_id,
                    alarm_panels.mac_address AS alarm_panels_mac_address,
                    alarm_panels.is_online AS alarm_panels_is_online
                FROM alarm_panels
                WHERE alarm_panels.mac_address = ?
                LIMIT ? OFFSET ?
            ) AS anon_1
            LEFT OUTER JOIN sensors AS sensors_1
                ON anon_1.alarm_panels_id = sensors_1.panel_id
            """,
            ("00:11:22:33:44:55", 1, 0),
        ),
        strict=False,
    )
