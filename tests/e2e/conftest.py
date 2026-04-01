import pytest
from sqlalchemy import create_engine
from pytest_capquery.plugin import CapQueryWrapper

@pytest.fixture(scope="session")
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()

@pytest.fixture(scope="session")
def postgres_engine():
    engine = create_engine("postgresql+psycopg2://postgres@localhost:5432/capquery_test")
    yield engine
    engine.dispose()

@pytest.fixture(scope="session")
def mysql_engine():
    engine = create_engine("mysql+pymysql://root:root@localhost:3306/capquery_test")
    yield engine
    engine.dispose()

@pytest.fixture(params=["sqlite_engine", "postgres_engine", "mysql_engine"])
def engine(request):
    return request.getfixturevalue(request.param)

@pytest.fixture
def e2e_capquery(engine):
    with CapQueryWrapper(engine) as captured:
        yield captured
