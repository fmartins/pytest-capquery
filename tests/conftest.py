import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker

from tests.models import Base

@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(db_engine):
    SessionMaker = sessionmaker(bind=db_engine)
    session = SessionMaker()
    yield session
    session.rollback()
    session.close()
