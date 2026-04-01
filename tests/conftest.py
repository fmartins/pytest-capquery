import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.pool import StaticPool

from pytest_capquery.plugin import CapQueryWrapper
from tests.models import Base


# ========================
# SQLITE FIXTURES (Shared across unit & e2e)
# ========================

@pytest.fixture(scope="session")
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sqlite_session(sqlite_engine):
    SessionMaker = sessionmaker(bind=sqlite_engine)
    session = SessionMaker()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def db_session(sqlite_session):
    """Alias for unit tests."""
    return sqlite_session


@pytest.fixture(scope="function")
def sqlite_capquery(sqlite_engine):
    with CapQueryWrapper(sqlite_engine) as captured:
        yield captured
