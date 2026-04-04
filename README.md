# pytest-capquery

![Build Status](https://github.com/fmartins/pytest-capquery/actions/workflows/ci.yml/badge.svg)
[![Codecov](https://codecov.io/gh/fmartins/pytest-capquery/graph/badge.svg)](https://codecov.io/gh/fmartins/pytest-capquery)
![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)

Testing your business logic is good, but **documenting and testing your database interactions is
critical**.

`pytest-capquery` treats your SQL queries as first-class citizens in your Pytest suite. By capturing
and asserting the exact queries executed, you create a living documentation of what is truly
happening behind the ORM abstraction.

This plugin does not force any specific SQLAlchemy architectural changes or optimization strategies.
It delegates all design decisions to the developer, acting strictly as a deterministic guardrail.
Once you've optimized your query footprint, `pytest-capquery` locks it in, ensuring cross-dialect
equality, validating exact transaction boundaries (`BEGIN`, `COMMIT`, `ROLLBACK`), and catching
silent N+1 regressions the second they are introduced.

## Key Features

- **Contextual Isolation:** Use the `capture()` context manager to track queries locally without
  global state leakage or manual resets.
- **SQL Snapshots:** Automatically generate and track expected `.sql` snapshots to easily document
  executed queries without cluttering test files.
- **Strict Timeline Assertion:** Validate the exact chronological sequence of SQL strings and
  transaction events.
- **Auto-Generating Assertions:** When explicit assertions fail, the plugin drops a fully formatted,
  copy-paste-ready Python block into stdout.
- **Heuristic Guards:** Use "loose assertion" mode to enforce maximum query counts.

## Used By

`pytest-capquery` is actively used to protect the database performance of:

- [macafe.cloud](https://macafe.cloud/)

---

## Installation

Install via pip:

```bash
pip install pytest-capquery
```

## Quick Start

The plugin does not provide a default database fixture, as it is designed to adapt to your specific
SQLAlchemy topology. You **must** define a global fixture in your `conftest.py` to bind
`pytest-capquery` to your project's database engine.

Quick references:

- [Pytest fixture configuring the DB engine & Capquery context](https://github.com/fmartins/pytest-capquery/blob/main/tests/e2e/postgres/conftest.py)
- [Test sample using the capquery snapshot support](https://github.com/fmartins/pytest-capquery/blob/main/tests/e2e/postgres/test_snapshot.py)
- [Test asset for documentation and easy review of the DBA](https://github.com/fmartins/pytest-capquery/blob/main/tests/e2e/postgres/__capquery_snapshots__/test_snapshot/test_insert_and_select_snapshot.sql)
- [Test sample using the super verbose inline SQL](https://github.com/fmartins/pytest-capquery/blob/main/tests/e2e/postgres/test_assert_executed_queries.py)
  

### 1. Setting Up Your Fixture (`conftest.py`)

To intercept queries from your custom engine, use the `CapQueryWrapper` and inject the
`capquery_context` fixture (which automatically handles snapshot file resolution behind the scenes).

#### Standard Synchronous Engines

```python
import pytest
from pytest_capquery.plugin import CapQueryWrapper

@pytest.fixture(scope="function")
def postgres_capquery(postgres_engine, capquery_context):
    """Binds capquery to a custom PostgreSQL testing engine."""
    with CapQueryWrapper(postgres_engine, snapshot_manager=capquery_context) as captured:
        yield captured
```

#### Asynchronous Engines (`AsyncEngine`)

If your project uses SQLAlchemy's `AsyncEngine` (e.g., with `asyncpg` or `aiomysql`), you **must**
attach the wrapper to the underlying synchronous engine. SQLAlchemy does not support event listeners
directly on async engine proxies.

```python
import pytest
from pytest_capquery.plugin import CapQueryWrapper

@pytest.fixture(scope="function")
def async_pg_capquery(async_pg_engine, capquery_context):
    """
    Binds capquery to an AsyncEngine by intercepting the underlying .sync_engine.
    This prevents 'NotImplementedError: asynchronous events are not implemented' errors.
    """
    with CapQueryWrapper(async_pg_engine.sync_engine, snapshot_manager=capquery_context) as captured:
        yield captured
```

By following this pattern, your custom fixtures automatically inherit the full snapshot lifecycle,
error tracking, and CLI flags (`--capquery-update`) without needing to manually map test paths or
instantiate `SnapshotManager` objects.

### 2. Documenting with SQL Snapshots (Recommended)

The most efficient way to document and protect your queries is by utilizing physical snapshots. This
automatically compares execution behavior against tracked `.sql` files stored in a
`__capquery_snapshots__` directory.

Use the custom fixture you defined (e.g., `postgres_capquery`) and the `capture()` context manager
to isolate specific execution phases.

```python
def test_update_user_status(postgres_session, postgres_capquery):
    # Enable assert_snapshot to verify execution against the disk
    with postgres_capquery.capture(assert_snapshot=True):
        user = postgres_session.query(User).filter_by(id=1).first()
        user.status = "active"
        postgres_session.commit()
```

**Workflow:** When writing a new test or updating existing query logic, run Pytest with the update
flag to automatically generate or overwrite the snapshot files:

```bash
pytest --capquery-update
```

Future runs without the flag will strictly assert that the runtime queries perfectly match the
generated `.sql` file.

### 3. Manual Explicit Assertions (Verbose)

If you prefer to explicitly document the executed SQL directly inside your test cases, you can use
strict manual assertions.

```python
def test_update_user_status(postgres_session, postgres_capquery):
    with postgres_capquery.capture() as phase:
        user = postgres_session.query(User).filter_by(id=1).first()
        user.status = "active"
        postgres_session.commit()

    # Verify the precise chronological timeline of the transaction
    phase.assert_executed_queries(
        "BEGIN",
        (
            """
            SELECT users.id, users.status
            FROM users
            WHERE users.id = %s
            """,
            (1,)
        ),
        (
            """
            UPDATE users SET status=%s WHERE users.id = %s
            """,
            ("active", 1)
        ),
        "COMMIT"
    )
```

**Auto-Generation on Failure:** Maintaining long SQL strings can be tedious. If your code changes
and the assertion fails, `pytest-capquery` will intercept the failure and drop the _correct_ Python
assertion block directly into your terminal's stdout. Simply copy and paste the block from your
terminal directly into your test to instantly fix the regression!

### 4. Preventing N+1 Queries (Loose Assertion)

If you want to protect a block of code against N+1 regressions without hardcoding exact SQL strings,
you can enforce a strict expected query count at the context boundary:

```python
def test_fetch_users(postgres_session, postgres_capquery):
    # Enforce that exactly 1 query is executed inside this block.
    # If a lazy-loading loop triggers extra queries, this will raise an AssertionError.
    with postgres_capquery.capture(expected_count=1):
        users = postgres_session.query(User).all()
        for user in users:
            _ = user.address
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

To get your local environment ready for contribution, run the following commands. We prioritize a
Test-Driven Development (TDD) workflow to continuously monitor database interactions.

```bash
# Clone the repository
git clone https://github.com/fmartins/pytest-capquery.git
cd pytest-capquery

# Install Python, dependencies, and pre-commit hooks
make setup

# Start the TDD watcher (auto-runs tests and updates snapshots on file changes)
make tdd
```

### Makefile Reference

```bash
make help

Usage:
  make <target>

Targets:
  help                 Show this help message
  setup                Full local setup: install pyenv python, create venv, and install deps
  setup-env            Install local python version via pyenv (macOS/Linux dev only)
  install              Create venv and install dependencies
  db-up                Start Docker Compose databases
  db-down              Tear down Docker Compose databases
  test                 Run all tests with code coverage and test analytics
  tdd                  Run tests in watch mode for test-driven development
  clean                Remove virtual environment and cached files
  format               Run formatters for python, markdown, yaml, and json files
  check-format         Check if files comply with formatting rules (for CI)
```

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International (CC BY-NC-SA 4.0)**.

Author: [Felipe Cardoso Martins](mailto:felipe.cardoso.martins@gmail.com)
