import pytest
from sqlalchemy import create_engine, text
from pytest_capquery.plugin import capquery


@pytest.fixture
def db_engine():
    return create_engine("sqlite:///:memory:")


def test_single_query(capquery, db_engine):
    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    capquery.assert_executed_queries("SELECT 1")
    capquery.assert_has_executed_query("select 1")


def test_multiple_queries(capquery, db_engine):
    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT 2"))

    capquery.assert_executed_queries("select    1", "select 2")


def test_commit(capquery, db_engine):
    with db_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested():
                conn.execute(text("SELECT 2"))

    capquery.assert_has_executed_query("SELECT 1")
    capquery.assert_has_executed_query("SELECT 2")
    capquery.assert_has_commit()


def test_nested_transaction_rollback(capquery, db_engine):
    with db_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 2"))
                # Rollback the nested transaction; does NOT emit a RELEASE SAVEPOINT
                nested.rollback()

    capquery.assert_has_executed_query("SELECT 1")
    capquery.assert_has_executed_query("SELECT 2")
    capquery.assert_has_no_commit()