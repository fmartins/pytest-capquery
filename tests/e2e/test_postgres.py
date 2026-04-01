from sqlalchemy.orm import joinedload
from tests.models import AlarmPanel, Sensor

def test_insert_and_select_normalization(postgres_session, postgres_capquery):
    # Action (Insert)
    panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
    sensor = Sensor(name="Front Door", sensor_type="Contact")
    panel.sensors.append(sensor)
    
    postgres_session.add(panel)
    postgres_session.flush()

    # Action (Select)
    queried_panel = postgres_session.query(AlarmPanel).options(joinedload(AlarmPanel.sensors)).filter_by(mac_address="00:11:22:33:44:55").first()
    assert queried_panel is not None

    statements = postgres_capquery.statements
    
    # 1. Insert AlarmPanel (Postgres uses named parameters dict normally and RETURNING id)
    panel_insert = next(s.statement for s in statements if "INSERT INTO alarm_panels" in s.statement)
    # 2. Insert Sensor
    sensor_insert = next(s.statement for s in statements if "INSERT INTO sensors" in s.statement)
    # 3. Select Panel
    panel_select = next(s.statement for s in statements if "SELECT " in s.statement and "FROM alarm_panels" in s.statement)

    # Note: Postgres driver format adaptation translates SQLAlchemy ORM objects into Dictionaries.
    postgres_capquery.assert_executed_queries(
        "BEGIN",
        (panel_insert, {"mac_address": "00:11:22:33:44:55", "is_online": True}),
        (sensor_insert, {"panel_id": 1, "name": "Front Door", "sensor_type": "Contact"}),
        (panel_select, {"mac_address_1": "00:11:22:33:44:55", "param_1": 1}),
        strict=False
    )
