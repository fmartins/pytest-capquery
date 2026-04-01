import pytest
from sqlalchemy import text
from pytest_capquery.plugin import CapQueryWrapper


def test_sqlite_cross_dialect_support(sqlite_engine):
    """
    Test parameter normalization specifically for SQLite using native Positional execution.
    """
    with sqlite_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("DROP TABLE IF EXISTS users"))
            conn.execute(text("CREATE TABLE users (name VARCHAR(50), age INT)"))
        
        with CapQueryWrapper(sqlite_engine) as capquery:
            with conn.begin():
                stmt_ins = "INSERT INTO users (name, age) VALUES (?, ?)"
                stmt_sel = "SELECT * FROM users WHERE name = ? AND age = ?"
                params = ("Alice", 30)

                conn.exec_driver_sql(stmt_ins, params)
                conn.exec_driver_sql(stmt_sel, params)

    captured = capquery.statements
    ins_stmt = next(s.statement for s in captured if "INSERT INTO" in s.statement.upper() and "USERS" in s.statement.upper())
    sel_stmt = next(s.statement for s in captured if "SELECT " in s.statement.upper() and "USERS" in s.statement.upper())

    capquery.assert_executed_queries(
        "BEGIN",
        (ins_stmt, ("Alice", 30)),
        (sel_stmt, ("Alice", 30)),
        "COMMIT"
    )


def test_postgres_cross_dialect_support(postgres_engine):
    """
    Without the plugin's `_normalize_params` fix, this assertion would fail 
    on PostgreSQL because psycopg2 returns a list `['Alice', 30]`, 
    while the expected parameter is logically the tuple `('Alice', 30)`.
    """
    with postgres_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("DROP TABLE IF EXISTS users"))
            conn.execute(text("CREATE TABLE users (name VARCHAR(50), age INT)"))
        
        with CapQueryWrapper(postgres_engine) as capquery:
            with conn.begin():
                stmt_ins = "INSERT INTO users (name, age) VALUES (%s, %s)"
                stmt_sel = "SELECT * FROM users WHERE name = %s AND age = %s"
                # Ensure it strictly runs correctly against normalized expected queries.
                params = ("Alice", 30)

                conn.exec_driver_sql(stmt_ins, params)
                conn.exec_driver_sql(stmt_sel, params)

    captured = capquery.statements
    ins_stmt = next(s.statement for s in captured if "INSERT INTO" in s.statement.upper() and "USERS" in s.statement.upper())
    sel_stmt = next(s.statement for s in captured if "SELECT " in s.statement.upper() and "USERS" in s.statement.upper())

    capquery.assert_executed_queries(
        "BEGIN",
        (ins_stmt, ("Alice", 30)),
        (sel_stmt, ("Alice", 30)),
        "COMMIT"
    )


def test_mysql_cross_dialect_support(mysql_engine):
    """
    Test parameter normalization specifically for MySQL.
    """
    with mysql_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("DROP TABLE IF EXISTS users"))
            conn.execute(text("CREATE TABLE users (name VARCHAR(50), age INT)"))
        
        with CapQueryWrapper(mysql_engine) as capquery:
            with conn.begin():
                stmt_ins = "INSERT INTO users (name, age) VALUES (%s, %s)"
                stmt_sel = "SELECT * FROM users WHERE name = %s AND age = %s"
                params = ("Alice", 30)

                conn.exec_driver_sql(stmt_ins, params)
                conn.exec_driver_sql(stmt_sel, params)

    captured = capquery.statements
    ins_stmt = next(s.statement for s in captured if "INSERT INTO" in s.statement.upper() and "USERS" in s.statement.upper())
    sel_stmt = next(s.statement for s in captured if "SELECT " in s.statement.upper() and "USERS" in s.statement.upper())

    capquery.assert_executed_queries(
        "BEGIN",
        (ins_stmt, ("Alice", 30)),
        (sel_stmt, ("Alice", 30)),
        "COMMIT"
    )
