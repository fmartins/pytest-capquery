# pytest-capquery

![Build Status](https://github.com/fmartins/pytest-capquery/actions/workflows/ci.yml/badge.svg)
[![Codecov](https://codecov.io/gh/fmartins/pytest-capquery/graph/badge.svg)](https://codecov.io/gh/fmartins/pytest-capquery)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)

Testing your business logic is good, but **testing your database interactions is critical**.

`pytest-capquery` treats your SQL queries as first-class citizens in your test suite. By asserting
the exact queries executed, you create living documentation of what is truly happening behind the
scenes. This guarantees deterministic performance, catches N+1 regressions instantly, and ensures
your application behaves exactly as intended.

Designed for modern Python applications, `pytest-capquery` is a strict, strongly-typed SQLAlchemy
pytest plugin that enforces exact chronological query execution, validating precise SQL strings,
parameter bindings, and transaction boundaries (`BEGIN`, `COMMIT`, `ROLLBACK`).

## Key Features

- **Contextual Isolation:** Use the `capture()` context manager to track queries locally without
  global state leakage or manual resets.
- **Strict Timeline Assertion:** Validate the exact chronological sequence of SQL strings and
  transaction events.
- **Heuristic N+1 Guards:** Use "loose assertion" mode to enforce maximum query counts without
  binding tests to fragile ORM implementation details.
- **Deterministic Parameter Matching:** Ensures cross-dialect equality for parameter structures.
- **Async Ready:** Seamlessly integrates with standard and `AsyncSession` environments.

## Used By

`pytest-capquery` is actively used to protect the database performance of:

- [macafe CLOUD](https://macafe.cloud/)

---

## Installation

Install via pip:

```bash
pip install pytest-capquery
```

## Quick Start

The `capquery` fixture captures all SQLAlchemy statements executed by your code. The best practice
is to use the `capture()` context manager to isolate specific execution phases.

### 1. Preventing N+1 Queries (Loose Assertion)

If you want to protect a block of code against N+1 regressions without hardcoding exact SQL strings,
you can enforce a strict expected query count at the context boundary:

```python
def test_fetch_users(sqlite_session, capquery):
    # Enforce that exactly 1 query is executed inside this block.
    # If a lazy-loading loop triggers extra queries, this will raise an AssertionError.
    with capquery.capture(expected_count=1):
        users = sqlite_session.query(User).all()
        for user in users:
            _ = user.address
```

### 2. Asserting Exact SQL Execution (Strict Assertion)

For mission-critical operations, you can capture a phase and rigorously assert the exact SQL and
parameters executed:

```python
def test_update_user_status(sqlite_session, capquery):
    with capquery.capture() as phase:
        user = sqlite_session.query(User).filter_by(id=1).first()
        user.status = "active"
        sqlite_session.commit()

    # Verify the precise chronological timeline of the transaction
    phase.assert_executed_queries(
        "BEGIN",
        (
            """
            SELECT users.id, users.status
            FROM users
            WHERE users.id = ?
            """,
            (1,)
        ),
        (
            """
            UPDATE users SET status=? WHERE users.id = ?
            """,
            ("active", 1)
        ),
        "COMMIT"
    )
```

---

## Contributing

We welcome contributions to make this plugin even better! To ensure a smooth process, please follow
these steps:

1. **Open an Issue:** Before writing any code, please open an issue to discuss the feature,
   enhancement, or bug fix you have in mind.
2. **Contribute the Code:** Once discussed, fork the repository, create your branch, make your
   changes, and submit a Pull Request.
3. **Review & Release:** All PRs will be reviewed. Once approved and merged, the release process
   will be managed by the maintainer.

### Developer Setup

To get your local environment ready for contribution, run the following commands:

```bash
# Clone the repository
git clone https://github.com/fmartins/pytest-capquery.git
cd pytest-capquery

# Install Python, dependencies, and pre-commit hooks
make setup

# Run the full test suite (handles DB spin-up and coverage)
make test
```

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International (CC BY-NC-SA 4.0)**.

Author: [Felipe Cardoso Martins](mailto:felipe.cardoso.martins@gmail.com)
