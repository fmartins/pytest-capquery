from sqlalchemy.orm import joinedload

from tests.models import AlarmPanel, Sensor

def test_insert_and_select_normalization(mysql_session, mysql_capquery):
    panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
    sensor = Sensor(name="Front Door", sensor_type="Contact")
    panel.sensors.append(sensor)

    mysql_session.add(panel)
    mysql_session.flush()

    queried_panel = mysql_session.query(AlarmPanel).options(joinedload(AlarmPanel.sensors)).filter_by(mac_address="00:11:22:33:44:55").first()
    assert queried_panel is not None

    mysql_capquery.assert_executed_queries(
        "BEGIN",
        (
            # language=SQL
            """
            INSERT INTO alarm_panels (mac_address, is_online)
            VALUES (%(mac_address)s, %(is_online)s)
            """,
            {"mac_address": "00:11:22:33:44:55", "is_online": 1}
        ),
        (
            # language=SQL
            """
            INSERT INTO sensors (panel_id, name, sensor_type)
            VALUES (%(panel_id)s, %(name)s, %(sensor_type)s)
            """,
            {"panel_id": 1, "name": "Front Door", "sensor_type": "Contact"}
        ),
        (
            # language=SQL
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
                WHERE alarm_panels.mac_address = %(mac_address_1)s
                LIMIT %(param_1)s
            ) AS anon_1
            LEFT OUTER JOIN sensors AS sensors_1
                ON anon_1.alarm_panels_id = sensors_1.panel_id
            """,
            {"mac_address_1": "00:11:22:33:44:55", "param_1": 1}
        ),
        strict=False
    )
