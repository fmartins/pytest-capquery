-- CAPQUERY: Query 1
-- EXPECTED_PARAMS: None
-- PHASE: 1
BEGIN

-- CAPQUERY: Query 2
-- EXPECTED_PARAMS: ('00:11:22:33:44:55', 1)
-- PHASE: 1
INSERT INTO alarm_panels (mac_address, is_online)
VALUES (?, ?)

-- CAPQUERY: Query 3
-- EXPECTED_PARAMS: (1, 'Front Door', 'Contact')
-- PHASE: 1
INSERT INTO sensors (panel_id, name, sensor_type)
VALUES (?, ?, ?)

-- CAPQUERY: Query 4
-- EXPECTED_PARAMS: ('00:11:22:33:44:55', 1, 0)
-- PHASE: 1
SELECT anon_1.alarm_panels_id AS anon_1_alarm_panels_id,
       anon_1.alarm_panels_mac_address AS anon_1_alarm_panels_mac_address,
       anon_1.alarm_panels_is_online AS anon_1_alarm_panels_is_online,
       sensors_1.id AS sensors_1_id,
       sensors_1.panel_id AS sensors_1_panel_id,
       sensors_1.name AS sensors_1_name,
       sensors_1.sensor_type AS sensors_1_sensor_type
FROM
  (SELECT alarm_panels.id AS alarm_panels_id,
          alarm_panels.mac_address AS alarm_panels_mac_address,
          alarm_panels.is_online AS alarm_panels_is_online
   FROM alarm_panels
   WHERE alarm_panels.mac_address = ?
   LIMIT ?
   OFFSET ?) AS anon_1
LEFT OUTER JOIN sensors AS sensors_1 ON anon_1.alarm_panels_id = sensors_1.panel_id
