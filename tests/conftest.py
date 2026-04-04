"""
Global pytest configuration and shared fixtures for the entire test suite.

This module provides common SQL database testing infrastructures, such as an in-memory
SQLite database fixture that is shared across both unit and end-to-end tests.
It ensures fixtures are constructed and torn down properly to prevent resource leakage.
"""

from pathlib import Path
from typing import Generator

import pytest

pytest.register_assert_rewrite("pytest_capquery.plugin")

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pytest_capquery.plugin import CapQueryWrapper
from pytest_capquery.snapshot import SnapshotManager
from tests.models import Base

pytest_plugins = ["pytest_capquery.plugin"]


@pytest.fixture(scope="session")
def sqlite_engine() -> Generator[Engine, None, None]:
    """
    Session-scoped fixture providing an in-memory SQLite SQLAlchemy engine.

    The engine leverages a StaticPool to ensure all references to the memory database
    access the exact same connection, permitting schema persistence across multiple
    connections. During teardown, the schema is dropped and the underlying DBAPI
    connection is explicitly terminated to prevent ResourceWarnings.
    """
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, echo=False)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sqlite_session(sqlite_engine: Engine) -> Generator[Session, None, None]:
    """
    Function-scoped fixture providing a localized SQLAlchemy Session.

    This ensures each test receives a clean transaction boundary. After the test yields,
    any open transaction is rolled back, and the session is formally closed.
    """
    SessionMaker = sessionmaker(bind=sqlite_engine)
    session = SessionMaker()

    yield session

    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def sqlite_capquery(request: pytest.FixtureRequest, sqlite_engine: Engine) -> Generator[CapQueryWrapper, None, None]:
    """
    Function-scoped fixture providing a CapQuery wrapper bound to the SQLite engine.

    Automatically intercepts and captures SQL statements and transaction events dispatched
    from the provided SQLite engine context.
    """
    update_mode = request.config.getoption("--capquery-update", default=False)
    snapshot_manager = SnapshotManager(
        nodeid=request.node.nodeid,
        test_path=Path(request.node.path),
        update_mode=update_mode
    )
    with CapQueryWrapper(sqlite_engine, snapshot_manager=snapshot_manager) as captured:
        yield captured
