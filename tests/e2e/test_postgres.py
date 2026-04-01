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

    postgres_capquery.assert_executed_queries(
        "BEGIN",
        (
            "INSERT INTO alarm_panels (mac_address, is_online) VALUES (%(mac_address)s, %(is_online)s) RETURNING alarm_panels.id", 
            {"mac_address": "00:11:22:33:44:55", "is_online": True}
        ),
        (
            "INSERT INTO sensors (panel_id, name, sensor_type) VALUES (%(panel_id)s, %(name)s, %(sensor_type)s) RETURNING sensors.id", 
            {"panel_id": 1, "name": "Front Door", "sensor_type": "Contact"}
        ),
        (
            "SELECT anon_1.alarm_panels_id AS anon_1_alarm_panels_id, anon_1.alarm_panels_mac_address AS anon_1_alarm_panels_mac_address, anon_1.alarm_panels_is_online AS anon_1_alarm_panels_is_online, sensors_1.id AS sensors_1_id, sensors_1.panel_id AS sensors_1_panel_id, sensors_1.name AS sensors_1_name, sensors_1.sensor_type AS sensors_1_sensor_type \nFROM (SELECT alarm_panels.id AS alarm_panels_id, alarm_panels.mac_address AS alarm_panels_mac_address, alarm_panels.is_online AS alarm_panels_is_online \nFROM alarm_panels \nWHERE alarm_panels.mac_address = %(mac_address_1)s \n LIMIT %(param_1)s) AS anon_1 LEFT OUTER JOIN sensors AS sensors_1 ON anon_1.alarm_panels_id = sensors_1.panel_id", 
            {"mac_address_1": "00:11:22:33:44:55", "param_1": 1}
        ),
        strict=False
    )
