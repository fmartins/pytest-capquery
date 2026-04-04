"""Global pytest configuration and shared fixtures for the entire test suite.

This module provides common SQL database testing infrastructures, such as an in-memory SQLite
database fixture that is shared across both unit and end-to-end tests. It ensures fixtures are
constructed and torn down properly to prevent resource leakage.
"""

import gc
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
    """Session-scoped fixture providing an in-memory SQLite SQLAlchemy engine.

    The engine leverages a StaticPool to ensure all references to the memory database access the
    exact same connection, permitting schema persistence across multiple connections. During
    teardown, the schema is dropped and the underlying DBAPI connection is explicitly terminated to
    prevent ResourceWarnings.
    """
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, echo=False)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sqlite_session(sqlite_engine: Engine) -> Generator[Session, None, None]:
    """Function-scoped fixture providing a localized SQLAlchemy Session.

    By returning to standard engine-binding, we preserve SQLAlchemy's natural `autobegin`
    timeline, which capquery relies on to capture the `BEGIN` statement exactly when the
    application triggers it.
    """
    SessionMaker = sessionmaker(bind=sqlite_engine)
    session = SessionMaker()

    yield session

    # Standard teardown
    session.rollback()
    session.close()

    # Force Python 3.13 Garbage Collection to sweep any lingering ORM objects mapped to the
    # session before Pytest tears down the scope. This safely eliminates the intermittent SQLite
    # ResourceWarnings without altering transactional boundaries.
    gc.collect()


@pytest.fixture(scope="function")
def sqlite_capquery(
    sqlite_engine: Engine, capquery_context: SnapshotManager
) -> Generator[CapQueryWrapper, None, None]:
    """Function-scoped fixture providing a CapQuery wrapper bound to the SQLite engine.

    Automatically intercepts and captures SQL statements and transaction events dispatched from the
    provided SQLite engine context, leveraging the globally provided snapshot context.
    """
    with CapQueryWrapper(sqlite_engine, snapshot_manager=capquery_context) as captured:
        yield captured
