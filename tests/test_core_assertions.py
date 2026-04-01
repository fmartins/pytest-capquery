import pytest
from sqlalchemy import text
from pytest_capquery.plugin import capquery


def test_single_query(capquery, db_engine):
    with db_engine.connect() as conn:
        conn.execute(text("SELECT :x"), {"x": 1})

    capquery.assert_total_queries(3)
    capquery.assert_executed_queries("BEGIN", "SELECT ?", "ROLLBACK")
    capquery.assert_has_executed_query("select ?", expected_params=(1,))


def test_multiple_queries(capquery, db_engine):
    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT 2"))

    capquery.assert_total_queries(4)
    capquery.assert_executed_queries("BEGIN", "select    1", "select 2", "ROLLBACK")


def test_commit(capquery, db_engine):
    with db_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested():
                conn.execute(text("SELECT 2"))

    capquery.assert_total_queries(8)
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

    capquery.assert_total_queries(8)
    capquery.assert_has_executed_query("SELECT 1")
    capquery.assert_has_executed_query("SELECT 2")
    capquery.assert_has_commit()


def test_complex_nested_transactions(capquery, db_engine):
    with db_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested():
                conn.execute(text("SELECT 2"))
                # simulates RELEASE SAVEPOINT
            
            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 3"))
                nested.rollback() # simulates ROLLBACK TO SAVEPOINT

    capquery.assert_total_queries(13)
    capquery.assert_has_executed_query("SELECT 1")
    capquery.assert_has_executed_query("SELECT 2")
    capquery.assert_has_executed_query("SELECT 3")
    capquery.assert_has_commit()


def test_transaction_begin_commit(capquery, db_engine):
    with db_engine.begin() as conn:
        conn.execute(text("SELECT 1"))

    capquery.assert_total_queries(3)
    capquery.assert_has_begin()
    capquery.assert_has_executed_query("SELECT 1")
    capquery.assert_has_commit()


def test_transaction_rollback(capquery, db_engine):
    conn = db_engine.connect()
    trans = conn.begin()
    conn.execute(text("SELECT 1"))
    trans.rollback()
    conn.close()

    capquery.assert_total_queries(3)
    capquery.assert_has_begin()
    capquery.assert_has_executed_query("SELECT 1")
    capquery.assert_has_rollback()
    capquery.assert_has_no_commit()


def test_nested_partial_rollback(capquery, db_engine):
    with db_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 2"))
                nested.rollback()
            conn.execute(text("SELECT 3"))

    capquery.assert_total_queries(9)
    capquery.assert_has_begin()
    capquery.assert_has_executed_query("SELECT 1")
    capquery.assert_has_executed_query("SELECT 2")
    capquery.assert_has_executed_query("SELECT 3")
    capquery.assert_has_commit()