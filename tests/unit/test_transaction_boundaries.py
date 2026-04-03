import pytest
from sqlalchemy import text


def test_single_query(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT :x"), {"x": 1})

    capquery.assert_executed_queries(
        "BEGIN",
        ("SELECT ?", (1,)),
        "ROLLBACK"
    )


def test_multiple_queries(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT 2"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SELECT 2",
        "ROLLBACK"
    )


def test_commit(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested():
                conn.execute(text("SELECT 2"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "RELEASE SAVEPOINT sa_savepoint_1",
        "COMMIT"
    )


def test_nested_transaction_rollback(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 2"))
                # Rollback the nested transaction; does NOT emit a RELEASE SAVEPOINT
                nested.rollback()

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "ROLLBACK TO SAVEPOINT sa_savepoint_1",
        "COMMIT"
    )


def test_complex_nested_transactions(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested():
                conn.execute(text("SELECT 2"))

            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 3"))
                nested.rollback()

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "RELEASE SAVEPOINT sa_savepoint_1",
        "SAVEPOINT sa_savepoint_2",
        "SELECT 3",
        "ROLLBACK TO SAVEPOINT sa_savepoint_2",
        "COMMIT"
    )


def test_transaction_begin_commit(capquery, sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(text("SELECT 1"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "COMMIT"
    )


def test_transaction_rollback(capquery, sqlite_engine):
    conn = sqlite_engine.connect()
    trans = conn.begin()
    conn.execute(text("SELECT 1"))
    trans.rollback()
    conn.close()

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "ROLLBACK"
    )


def test_nested_partial_rollback(capquery, sqlite_engine):
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT 1"))
            with conn.begin_nested() as nested:
                conn.execute(text("SELECT 2"))
                nested.rollback()
            conn.execute(text("SELECT 3"))

    capquery.assert_executed_queries(
        "BEGIN",
        "SELECT 1",
        "SAVEPOINT sa_savepoint_1",
        "SELECT 2",
        "ROLLBACK TO SAVEPOINT sa_savepoint_1",
        "SELECT 3",
        "COMMIT"
    )
