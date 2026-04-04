from tests.models import AlarmPanel, Sensor


def test_user_business_logic(db_session, capquery):
    """
    EXAMPLE: Standard Snapshot Workflow

    1. Write your test using `capquery.capture(assert_snapshot=True)`.
    2. Run `pytest --capquery-update` to generate the initial snapshot file.
    3. Commit the resulting `__capquery_snapshots__/test_snapshot_usage/test_user_business_logic.sql` file to Git.
    4. Future runs of `pytest` will automatically verify against that file.

    The initial panel setup is not captured, but the application code simulating
    the addition of a new sensor is wrapped in the capture context. The plugin
    automatically resolves the snapshot path and asserts the timeline at the
    context manager exit.
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
    EXAMPLE: Multiple Capture Phases

    You can use multiple capture blocks in a single test. The plugin will
    safely serialize all phases into a single, cohesive .sql snapshot file.
    This example demonstrates capturing a complex timeline with mixed usage
    of aliases to organize the snapshot output.
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
