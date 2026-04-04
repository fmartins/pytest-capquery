-- CAPQUERY: Query 1
-- EXPECTED_PARAMS: None
-- PHASE: 1 (Panel Setup Phase)
BEGIN

-- CAPQUERY: Query 2
-- EXPECTED_PARAMS: ('AA:BB:CC:DD:EE:FF', 1)
-- PHASE: 1 (Panel Setup Phase)
INSERT INTO alarm_panels (mac_address, is_online)
VALUES (?, ?)

-- CAPQUERY: Query 3
-- EXPECTED_PARAMS: (1,)
-- PHASE: 2
SELECT sensors.id AS sensors_id,
       sensors.panel_id AS sensors_panel_id,
       sensors.name AS sensors_name,
       sensors.sensor_type AS sensors_sensor_type
FROM sensors
WHERE ? = sensors.panel_id

-- CAPQUERY: Query 4
-- EXPECTED_PARAMS: (1, 'Living Room', 'Motion')
-- PHASE: 2
INSERT INTO sensors (panel_id, name, sensor_type)
VALUES (?, ?, ?) RETURNING id

-- CAPQUERY: Query 5
-- EXPECTED_PARAMS: (1, 'Back Door', 'Contact')
-- PHASE: 2
INSERT INTO sensors (panel_id, name, sensor_type)
VALUES (?, ?, ?) RETURNING id

-- CAPQUERY: Query 6
-- EXPECTED_PARAMS: (0, 1)
-- PHASE: 3 (Status Toggle and Deletion Phase)
UPDATE alarm_panels
SET is_online=?
WHERE alarm_panels.id = ?

-- CAPQUERY: Query 7
-- EXPECTED_PARAMS: (1,)
-- PHASE: 3 (Status Toggle and Deletion Phase)
DELETE
FROM sensors
WHERE sensors.id = ?
