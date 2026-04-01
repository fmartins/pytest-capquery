import pytest
from sqlalchemy import text

def test_dialect_parameter_normalization(e2e_capquery, engine):
    """
    Documentation test for dialect parameter normalization:
    When inserting/selecting values, SQLite DBAPI passes parameters as tuples,
    while psycopg2 (PostgreSQL) passes them as lists or dicts.
    With the `_normalize_params` fix, pytest-capquery safely unifies 
    both structures into natively comparable sorting formats. Without it, 
    this assertion would fail on PostgreSQL because psycopg2 returns a list `['Alice', 30]`, 
    while the expected parameter is logically the tuple `('Alice', 30)` (if passed sequentially).
    """
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("DROP TABLE IF EXISTS users"))
            conn.execute(text("CREATE TABLE users (name VARCHAR(50), age INT)"))
        
        with conn.begin():
            if engine.name == "sqlite":
                stmt_ins = "INSERT INTO users (name, age) VALUES (?, ?)"
                stmt_sel = "SELECT * FROM users WHERE name = ? AND age = ?"
                params = ("Alice", 30)
            elif engine.name == "postgresql":
                stmt_ins = "INSERT INTO users (name, age) VALUES (%s, %s)"
                stmt_sel = "SELECT * FROM users WHERE name = %s AND age = %s"
                params = ("Alice", 30)  # Positional tuple for PostgreSQL
            elif engine.name == "mysql":
                stmt_ins = "INSERT INTO users (name, age) VALUES (%s, %s)"
                stmt_sel = "SELECT * FROM users WHERE name = %s AND age = %s"
                params = ("Alice", 30)

            conn.exec_driver_sql(stmt_ins, params)
            conn.exec_driver_sql(stmt_sel, params)

    captured = e2e_capquery.statements
    ins_stmt = next(s.statement for s in captured if "INSERT INTO" in s.statement.upper() and "USERS" in s.statement.upper())
    sel_stmt = next(s.statement for s in captured if "SELECT " in s.statement.upper() and "USERS" in s.statement.upper())

    e2e_capquery.assert_executed_queries(
        "BEGIN",
        "DROP TABLE IF EXISTS users",
        "CREATE TABLE users (name VARCHAR(50), age INT)",
        "COMMIT",
        "BEGIN",
        (ins_stmt, ("Alice", 30)),
        (sel_stmt, ("Alice", 30)),
        "COMMIT"
    )
