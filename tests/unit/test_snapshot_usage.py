from tests.models import AlarmPanel, Sensor


def test_user_business_logic(db_session, capquery):
    """
    EXAMPLE: Standard Snapshot Workflow

    1. Write your test using `capquery.capture(assert_snapshot=True)`.
    2. Run `pytest --capquery-update` to generate the initial snapshot file.
    3. Commit the resulting `__capquery_snapshots__/test_snapshot_usage/test_user_business_logic.sql` file to Git.
    4. Future runs of `pytest` will automatically verify against that file.
    """
    # 1. Setup test data (not captured)
    panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
    db_session.add(panel)
    db_session.flush()

    # 2. Start capturing the queries we care about
    with capquery.capture(assert_snapshot=True):
        # Simulate application code running
        sensor = Sensor(name="Front Door", sensor_type="Contact")
        panel.sensors.append(sensor)
        db_session.flush()

    # 3. The plugin automatically resolves the snapshot path and asserts the timeline at the context manager exit


def test_user_multiple_phases(db_session, capquery):
    """
    EXAMPLE: Multiple Capture Phases

    You can use multiple capture blocks in a single test. The plugin will
    safely serialize all phases into a single, cohesive .sql snapshot file.
    """
    panel = AlarmPanel(mac_address="AA:BB:CC:DD:EE:FF", is_online=True)

    with capquery.capture(assert_snapshot=True):
        db_session.add(panel)
        db_session.flush()

    with capquery.capture(assert_snapshot=True):
        panel.is_online = False
        db_session.flush()

    # Both phases assert against their specific segment of the snapshot automatically
