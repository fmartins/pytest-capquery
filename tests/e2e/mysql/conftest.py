"""End-to-end testing fixtures for MySQL database validation.

This module provisions a tangible MySQL database engine, enabling integration tests to accurately
replicate production-grade execution topologies. All open connections and pools are explicitly
invalidated during teardown to maintain environment integrity and suppress system resource warnings.
"""

from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import Session, sessionmaker

from pytest_capquery.plugin import CapQueryWrapper
from pytest_capquery.snapshot import SnapshotManager
from tests.models import Base


@pytest.fixture(scope="session")
def mysql_engine() -> Generator[Engine, None, None]:
    """Provision a MySQL integration database engine.

    The fixture performs full DDL initialization upon startup and guarantees explicit pool disposal
    and metadata dropping upon completion.
    """
    engine = create_engine("mysql+pymysql://root:root@localhost:3306/capquery_test")
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def mysql_session(mysql_engine: Engine) -> Generator[Session, None, None]:
    """Provision an isolated SQLAlchemy Session utilizing the MySQL engine.

    Provides a clean transactional boundary for individual test runs. It forcefully rolls back open
    transactions preventing contamination between integration tests, and authentically truncates
    resetting auto-increment thresholds flawlessly.
    """
    SessionMaker = sessionmaker(bind=mysql_engine)
    session = SessionMaker()
    session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    session.execute(text("TRUNCATE TABLE alarm_panels;"))
    session.execute(text("TRUNCATE TABLE sensors;"))
    session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    session.execute(text("ALTER TABLE alarm_panels AUTO_INCREMENT = 1;"))
    session.execute(text("ALTER TABLE sensors AUTO_INCREMENT = 1;"))
    session.commit()

    yield session

    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def mysql_capquery(
    request: pytest.FixtureRequest, mysql_engine: Engine
) -> Generator[CapQueryWrapper, None, None]:
    """Provide an engine-bound CapQuery interception interface for MySQL.

    Catches and tracks PyMySQL Dialect queries executed through the provisioned engine.
    """
    update_mode = request.config.getoption("--capquery-update", default=False)
    snapshot_manager = SnapshotManager(
        nodeid=request.node.nodeid, test_path=Path(request.node.path), update_mode=update_mode
    )
    with CapQueryWrapper(mysql_engine, snapshot_manager=snapshot_manager) as captured:
        yield captured
