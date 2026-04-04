-- CAPQUERY: Query 1
-- EXPECTED_PARAMS: (1,)
-- PHASE: 1
SELECT sensors.id AS sensors_id,
       sensors.panel_id AS sensors_panel_id,
       sensors.name AS sensors_name,
       sensors.sensor_type AS sensors_sensor_type
FROM sensors
WHERE ? = sensors.panel_id

-- CAPQUERY: Query 2
-- EXPECTED_PARAMS: (1, 'Front Door', 'Contact')
-- PHASE: 1
INSERT INTO sensors (panel_id, name, sensor_type)
VALUES (?, ?, ?)
