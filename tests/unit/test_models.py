"""
Validation of complex dynamic SQLAlchemy internal execution mechanics.

This module rigorously proves mapping interactions between Python models and
intercepted raw DBAPI expressions correctly match declarative structures reliably
across complicated joined loads and multi-transaction loops securely.
"""
from sqlalchemy.orm import joinedload

from tests.models import AlarmPanel, Sensor


def test_orm_insert(sqlite_session, capquery):
    """
    Ensures that standard sequential class-based object insertions resolve distinctly
    to correct parameter tuple bounds perfectly matching standard SQL generation paths.
    """
    panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
    sensor1 = Sensor(name="Front Door", sensor_type="Contact")
    sensor2 = Sensor(name="Living Room", sensor_type="Motion")
    panel.sensors.extend([sensor1, sensor2])

    sqlite_session.add(panel)

    capquery.statements.clear()
    sqlite_session.flush()

    capquery.assert_executed_queries(
        "BEGIN",
        (
            """
            INSERT INTO alarm_panels (mac_address, is_online)
            VALUES (?, ?)
            """,
            ("00:11:22:33:44:55", 1)
        ),
        (
            """
            INSERT INTO sensors (panel_id, name, sensor_type)
            VALUES (?, ?, ?) RETURNING id
            """,
            (1, "Front Door", "Contact")
        ),
        (
            """
            INSERT INTO sensors (panel_id, name, sensor_type)
            VALUES (?, ?, ?) RETURNING id
            """,
            (1, "Living Room", "Motion")
        )
    )


def test_orm_update(sqlite_session, capquery):
    """
    Confirms targeted object parameter replacement automatically delegates strict
    SQL update strings precisely bounded against verified schema definitions continuously.
    """
    panel = AlarmPanel(mac_address="AA:BB:CC:DD:EE:FF", is_online=False)
    sqlite_session.add(panel)
    sqlite_session.flush()
    capquery.statements.clear()

    panel = sqlite_session.query(AlarmPanel).filter_by(mac_address="AA:BB:CC:DD:EE:FF").first()
    panel.is_online = True
    sqlite_session.flush()

    capquery.assert_executed_queries(
        (
            """
            SELECT
                alarm_panels.id AS alarm_panels_id,
                alarm_panels.mac_address AS alarm_panels_mac_address,
                alarm_panels.is_online AS alarm_panels_is_online
            FROM alarm_panels
            WHERE alarm_panels.mac_address = ?
            LIMIT ? OFFSET ?
            """,
            ("AA:BB:CC:DD:EE:FF", 1, 0)
        ),
        (
            """
            UPDATE alarm_panels
            SET is_online=?
            WHERE alarm_panels.id = ?
            """,
            (1, 1)
        )
    )


def test_orm_delete(sqlite_session, capquery):
    """
    Validates cascaded removal triggers corresponding object deletion queries cleanly
    leaving exact session markers fully transparent for regression checking layers.
    """
    panel = AlarmPanel(mac_address="11:22:33:44:55:66", is_online=True)
    sensor = Sensor(name="Back Door", sensor_type="Contact")
    panel.sensors.append(sensor)
    sqlite_session.add(panel)
    sqlite_session.flush()

    capquery.statements.clear()

    sensor_to_delete = sqlite_session.query(Sensor).filter_by(name="Back Door").first()
    sqlite_session.delete(sensor_to_delete)
    sqlite_session.flush()

    capquery.assert_executed_queries(
        (
            """
            SELECT
                sensors.id AS sensors_id,
                sensors.panel_id AS sensors_panel_id,
                sensors.name AS sensors_name,
                sensors.sensor_type AS sensors_sensor_type
            FROM sensors
            WHERE sensors.name = ?
            LIMIT ? OFFSET ?
            """,
            ("Back Door", 1, 0)
        ),
        (
            """
            DELETE FROM sensors
            WHERE sensors.id = ?
            """,
            (1,)
        )
    )


def test_orm_select(sqlite_session, capquery):
    """
    Assures simple declarative fetching routines bypass unnecessary engine overheads,
    directly exposing concise limiting offset targets deterministically properly.
    """
    panel = AlarmPanel(mac_address="22:33:44:55:66:77", is_online=False)
    sqlite_session.add(panel)
    sqlite_session.flush()

    capquery.statements.clear()

    fetched_panel = sqlite_session.query(AlarmPanel).filter_by(mac_address="22:33:44:55:66:77").first()

    assert fetched_panel is not None
    capquery.assert_executed_queries(
        (
            """
            SELECT
                alarm_panels.id AS alarm_panels_id,
                alarm_panels.mac_address AS alarm_panels_mac_address,
                alarm_panels.is_online AS alarm_panels_is_online
            FROM alarm_panels
            WHERE alarm_panels.mac_address = ?
            LIMIT ? OFFSET ?
            """,
            ("22:33:44:55:66:77", 1, 0)
        )
    )


def test_avoid_n_plus_one_queries(sqlite_session, capquery):
    """
    Simulates optimized bulk ingestion loading architectures, effectively asserting
    joined-load configuration successfully prevents N+1 execution disasters logically.
    """
    for i in range(3):
        panel = AlarmPanel(mac_address=f"00:00:00:00:00:0{i}", is_online=True)
        sensors = [Sensor(name=f"Sensor {j}", sensor_type="Contact") for j in range(5)]
        panel.sensors.extend(sensors)
        sqlite_session.add(panel)
    sqlite_session.flush()
    sqlite_session.expunge_all()

    capquery.statements.clear()

    panels = sqlite_session.query(AlarmPanel).options(joinedload(AlarmPanel.sensors)).all()

    for panel in panels:
        _ = panel.sensors
        for sensor in panel.sensors:
            _ = sensor.name

    capquery.assert_executed_queries(
        """
        SELECT
            alarm_panels.id AS alarm_panels_id,
            alarm_panels.mac_address AS alarm_panels_mac_address,
            alarm_panels.is_online AS alarm_panels_is_online,
            sensors_1.id AS sensors_1_id,
            sensors_1.panel_id AS sensors_1_panel_id,
            sensors_1.name AS sensors_1_name,
            sensors_1.sensor_type AS sensors_1_sensor_type
        FROM alarm_panels
        LEFT OUTER JOIN sensors AS sensors_1
            ON alarm_panels.id = sensors_1.panel_id
        """
    )


def test_demonstrate_n_plus_one_problem(sqlite_session, capquery):
    """
    Establishes an intentional N+1 failure proving the execution tracer successfully
    chronicles repeating redundant queries reliably exposing bad optimization architectures.
    """
    for i in range(3):
        panel = AlarmPanel(mac_address=f"00:00:00:00:00:0{i}", is_online=True)
        sensors = [Sensor(name=f"Sensor {j}", sensor_type="Contact") for j in range(5)]
        panel.sensors.extend(sensors)
        sqlite_session.add(panel)
    sqlite_session.flush()
    sqlite_session.expunge_all()

    capquery.statements.clear()

    panels = sqlite_session.query(AlarmPanel).all()

    for panel in panels:
        _ = panel.sensors
        for sensor in panel.sensors:
            _ = sensor.name

    capquery.assert_executed_queries(
        """
        SELECT
            alarm_panels.id AS alarm_panels_id,
            alarm_panels.mac_address AS alarm_panels_mac_address,
            alarm_panels.is_online AS alarm_panels_is_online
        FROM alarm_panels
        """,
        (
            """
            SELECT
                sensors.id AS sensors_id,
                sensors.panel_id AS sensors_panel_id,
                sensors.name AS sensors_name,
                sensors.sensor_type AS sensors_sensor_type
            FROM sensors
            WHERE ? = sensors.panel_id
            """,
            (1,)
        ),
        (
            """
            SELECT
                sensors.id AS sensors_id,
                sensors.panel_id AS sensors_panel_id,
                sensors.name AS sensors_name,
                sensors.sensor_type AS sensors_sensor_type
            FROM sensors
            WHERE ? = sensors.panel_id
            """,
            (2,)
        ),
        (
            """
            SELECT
                sensors.id AS sensors_id,
                sensors.panel_id AS sensors_panel_id,
                sensors.name AS sensors_name,
                sensors.sensor_type AS sensors_sensor_type
            FROM sensors
            WHERE ? = sensors.panel_id
            """,
            (3,)
        )
    )
