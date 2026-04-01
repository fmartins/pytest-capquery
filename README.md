# pytest-capquery

![Build Status](https://github.com/fmartins/pytest-capquery/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)

`pytest-capquery` is a strict, strongly-typed SQLAlchemy pytest plugin designed to enforce exact
chronological query execution and catch N+1 regressions. By asserting precise SQL strings, parameter
bindings, and transaction boundaries (`BEGIN`, `COMMIT`, `ROLLBACK`), `pytest-capquery` guarantees
that your database interactions behave exactly as intended.

## Installation

Install via pip:

```bash
pip install pytest-capquery
```

## Quick Start

The `capquery` fixture captures all SQLAlchemy statements executed by your code. You can use it to
assert precise SQL queries, exact bound parameters, and transaction events in deterministic order.

Here is how you can use the `capquery` fixture alongside your SQLAlchemy models (e.g., `AlarmPanel`
and `Sensor`):

```python
from sqlalchemy.orm import Session
from tests.models import AlarmPanel, Sensor

def test_insert_alarm_panel(db_session: Session, capquery):
    # Setup
    panel = AlarmPanel(mac_address="00:11:22:33:44:55", is_online=True)
    sensor = Sensor(name="Front Door", sensor_type="Contact")
    panel.sensors.append(sensor)

    db_session.add(panel)

    # Clear any unrelated previous queries
    capquery.statements.clear()

    # Trigger database flush
    db_session.flush()

    # Assert exact chronological execution, parameters, and transaction boundaries
    capquery.assert_executed_queries(
        "BEGIN",
        (
            "INSERT INTO alarm_panels (mac_address, is_online) VALUES (?, ?)",
            ("00:11:22:33:44:55", 1)
        ),
        (
            "INSERT INTO sensors (panel_id, name, sensor_type) VALUES (?, ?, ?) RETURNING id",
            (1, "Front Door", "Contact")
        )
    )
```

## The N+1 Problem Showcase

One of the most powerful use cases for `pytest-capquery` is catching performance regressions
associated with the 1+N lazy-loading problem. It clearly contrasts inefficient DB loops with
optimized joined-loading.

### Catching a 1+N Lazy-Loading Regression

If a developer drops the `joinedload` behavior, `pytest-capquery` will expose the exact 1+N
lazy-loading queries:

```python
def test_demonstrate_n_plus_one_problem(db_session: Session, capquery):
    capquery.statements.clear()

    # Query all panels WITHOUT eagerly loading sensors
    panels = db_session.query(AlarmPanel).all()

    # Accessing the lazy relationship triggers N+1 queries
    for panel in panels:
        _ = panel.sensors

    # Asserting the resulting N+1 problem
    capquery.assert_executed_queries(
        # The 1 Query
        "SELECT alarm_panels.id AS alarm_panels_id, "
        "alarm_panels.mac_address AS alarm_panels_mac_address, "
        "alarm_panels.is_online AS alarm_panels_is_online "
        "FROM alarm_panels",

        # The +N Queries
        (
            "SELECT sensors.id AS sensors_id, "
            "sensors.panel_id AS sensors_panel_id, "
            "sensors.name AS sensors_name, "
            "sensors.sensor_type AS sensors_sensor_type "
            "FROM sensors "
            "WHERE ? = sensors.panel_id",
            (1,)
        ),
        (
            "SELECT sensors.id AS sensors_id, "
            "sensors.panel_id AS sensors_panel_id, "
            "sensors.name AS sensors_name, "
            "sensors.sensor_type AS sensors_sensor_type "
            "FROM sensors "
            "WHERE ? = sensors.panel_id",
            (2,)
        ),
        (
            "SELECT sensors.id AS sensors_id, "
            "sensors.panel_id AS sensors_panel_id, "
            "sensors.name AS sensors_name, "
            "sensors.sensor_type AS sensors_sensor_type "
            "FROM sensors "
            "WHERE ? = sensors.panel_id",
            (3,)
        )
    )
```

### Fixing the N+1 problem with joined-loading

When developers optimize their query with `joinedload`, `pytest-capquery` verifies the problem is
fixed:

```python
from sqlalchemy.orm import joinedload

def test_avoid_n_plus_one_queries(db_session: Session, capquery):
    capquery.statements.clear()

    # Query WITH eager loading
    panels = db_session.query(AlarmPanel).options(joinedload(AlarmPanel.sensors)).all()

    # Accessing the relationship no longer triggers additional queries
    for panel in panels:
        _ = panel.sensors

    # Asserting only a single JOIN query was executed
    capquery.assert_executed_queries(
        "SELECT alarm_panels.id AS alarm_panels_id, "
        "alarm_panels.mac_address AS alarm_panels_mac_address, "
        "alarm_panels.is_online AS alarm_panels_is_online, "
        "sensors_1.id AS sensors_1_id, "
        "sensors_1.panel_id AS sensors_1_panel_id, "
        "sensors_1.name AS sensors_1_name, "
        "sensors_1.sensor_type AS sensors_1_sensor_type "
        "FROM alarm_panels "
        "LEFT OUTER JOIN sensors AS sensors_1 ON alarm_panels.id = sensors_1.panel_id"
    )
```

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International (CC BY-NC-SA 4.0)**. Author: fmartins
