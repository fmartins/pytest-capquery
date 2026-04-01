import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pytest_capquery.plugin import CapQueryWrapper
from tests.models import Base

# ========================
# ENGINE INSTANTIATION
# ========================

from sqlalchemy.pool import StaticPool

@pytest.fixture(scope="session")
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="session")
def postgres_engine():
    engine = create_engine("postgresql+psycopg2://postgres@localhost:5432/capquery_test")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="session")
def mysql_engine():
    engine = create_engine("mysql+pymysql://root:root@localhost:3306/capquery_test")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

# ========================
# SESSION INSTANTIATION
# ========================

@pytest.fixture(scope="function")
def sqlite_session(sqlite_engine):
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="function")
def postgres_session(postgres_engine):
    Session = sessionmaker(bind=postgres_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="function")
def mysql_session(mysql_engine):
    Session = sessionmaker(bind=mysql_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

# ========================
# CAPQUERY FIXTURES
# ========================

@pytest.fixture(scope="function")
def sqlite_capquery(sqlite_engine):
    with CapQueryWrapper(sqlite_engine) as captured:
        yield captured

@pytest.fixture(scope="function")
def postgres_capquery(postgres_engine):
    with CapQueryWrapper(postgres_engine) as captured:
        yield captured

@pytest.fixture(scope="function")
def mysql_capquery(mysql_engine):
    with CapQueryWrapper(mysql_engine) as captured:
        yield captured
