from sqlalchemy.orm import joinedload
from tests.models import AlarmPanel, Sensor

def test_insert_and_select_normalization(sqlite_session, sqlite_capquery):
    # Action (Insert)
    panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
    sensor = Sensor(name="Front Door", sensor_type="Contact")
    panel.sensors.append(sensor)
    
    sqlite_session.add(panel)
    sqlite_session.flush()

    # Action (Select)
    queried_panel = sqlite_session.query(AlarmPanel).options(joinedload(AlarmPanel.sensors)).filter_by(mac_address="00:11:22:33:44:55").first()
    assert queried_panel is not None

    # Assert queries precisely compiled via the dialect
    statements = sqlite_capquery.statements
    
    # 1. Insert AlarmPanel
    panel_insert = next(s.statement for s in statements if "INSERT INTO alarm_panels" in s.statement)
    # 2. Insert Sensor
    sensor_insert = next(s.statement for s in statements if "INSERT INTO sensors" in s.statement)
    # 3. Select Panel
    panel_select = next(s.statement for s in statements if "SELECT " in s.statement and "FROM alarm_panels" in s.statement)

    sqlite_capquery.assert_executed_queries(
        "BEGIN",
        (panel_insert, ("00:11:22:33:44:55", True)),  # SQLite DBAPI format
        (sensor_insert, (1, "Front Door", "Contact")),
        (panel_select, ("00:11:22:33:44:55", 1, 0)),
        strict=False  # We just care about these specific executed queries in order
    )
