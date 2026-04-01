"""
Pytest Capquery Plugin.

License: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
Author: Felipe Cardoso Martins <felipe.cardoso.martins@gmail.com>

This module provides the core functionality for capturing and asserting upon
SQL statements executed via SQLAlchemy within pytest test cases. It intercepts and
formats queries to help rigorously monitor and test database interactions,
preventing N+1 query issues and ensuring precise transaction boundaries.
"""

import functools
from dataclasses import dataclass
from typing import Any, Sequence, Tuple, Union, Optional, Dict, Callable, List, cast, Protocol, runtime_checkable

import pytest
import sqlparse
from sqlalchemy import event, Connection, Engine
from sqlalchemy_capture_sql import CaptureSqlStatements


format_query = functools.partial(sqlparse.format, reindent=True, keyword_case="upper")


def reformat_query(query: str) -> str:
    """
    Reformats a SQL query string for standardized comparison and readability.

    Args:
        query (str): The raw SQL query string to be formatted.

    Raises:
        ValueError: If more than one executable SQL statement is present.

    Returns:
        str: The formatted SQL query string, or an empty string if there are no statements.
    """
    query = query.strip()
    parsed = sqlparse.parse(query)

    statements = [p for p in parsed if str(p).strip()]
    if len(statements) > 1:
        raise ValueError("Only one query is allowed.")

    if not statements:
        return ""

    return format_query(query)


def _normalize_params(params: Any) -> Any:
    """
    Recursively normalizes parameter structures to ensure cross-dialect equality.

    When comparing query parameters across different database backends (e.g.,
    SQLite vs Postgres), their structures often differ. This normalization
    ensures strict deterministic equality checks regardless of the SQL dialect.

    - Dicts: Sorted by key into a tuple of tuples.
    - Lists/Tuples: Converted to tuples, recursive normalization applied to elements.
    - Other types are left as-is.

    Args:
        params (Any): The query parameters to be normalized.

    Returns:
        Any: A standardized, immutable representation of the parameters.
    """
    if isinstance(params, dict):
        return tuple(sorted((k, _normalize_params(v)) for k, v in params.items()))
    elif isinstance(params, (list, tuple)):
        return tuple(_normalize_params(v) for v in params)
    return params


@runtime_checkable
class CapturedStmt(Protocol):
    """
    Strict protocol defining a captured SQL statement or transaction event.

    Attributes:
        statement (str): The raw SQL string or event name (e.g., 'BEGIN').
        parameters (Any): Bound parameters accompanying the statement.
    """
    @property
    def statement(self) -> str:
        ...

    @property
    def parameters(self) -> Any:
        ...


@dataclass
class NormalizedStringStmt:
    """
    Internal normalized representation for raw string statements.

    Used to wrap raw strings yielded by backend systems into a dataclass
    matching the CapturedStmt protocol.
    """
    statement: str
    parameters: Any = None


class TxEvent:
    """
    Wrapper for transaction events to match the CapturedStmt protocol.

    This ensures that explicit transaction events like BEGIN or COMMIT expose
    the rigorous `statement` and `parameters` properties required for timeline testing.
    """
    def __init__(self, stmt: str) -> None:
        """
        Initializes a new transaction event.

        Args:
            stmt (str): The uppercase transaction event string (e.g., "BEGIN").
        """
        self.statement: str = stmt
        self.parameters: Optional[Union[Sequence[Any], Dict[str, Any]]] = None
        self.idx: int = id(self)
        self.duration: float = 0.0
        self.first_table: str = "N/A"
        self.sql_type: str = "EVENT"

    def set_tst_next(self, now: Any) -> None:
        """
        Hook used for tracking timestamps between subsequent events.

        Args:
            now (Any): Current timestamp.
        """
        pass


class CapQueryWrapper(CaptureSqlStatements):
    """
    A context manager and SQLAlchemy event listener for capturing executed queries.

    This class runs at the boundary of SQLAlchemy engines, intercepting query 
    events in real time while pushing explicit transaction logs (BEGIN, COMMIT) 
    into a unified collection timeline.

    It exposes rigorous assertion methods to ensure an explicit chronological 
    execution order, safeguarding ORMs against N+1 regression patterns and 
    excessive transaction footprints.
    """
    _listeners: Dict[str, Callable[[Connection], None]]

    def __enter__(self) -> "CapQueryWrapper":
        """
        Enters the context manager and registers transaction event listeners.

        Returns:
            CapQueryWrapper: The active wrapper capturing queries.
        """
        super().__enter__()
        
        self._listeners = {
            "begin": lambda conn: self.statements.append(TxEvent("BEGIN")),
            "commit": lambda conn: self.statements.append(TxEvent("COMMIT")),
            "rollback": lambda conn: self.statements.append(TxEvent("ROLLBACK")),
        }
        for name, fn in self._listeners.items():
            event.listen(self.engine, name, fn)
            
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exits the context manager and cleans up bound SQLAlchemy listeners.
        """
        for name, fn in self._listeners.items():
            event.remove(self.engine, name, fn)
        super().__exit__(exc_type, exc_val, exc_tb)

    def _normalize_statement(self, item: Any) -> CapturedStmt:
        """
        Internally coerces parsed statements into the CapturedStmt protocol.

        Args:
            item (Any): Raw output appended to self.statements.

        Returns:
            CapturedStmt: The safely typed object with .statement and .parameters access.
        """
        if isinstance(item, str):
            return cast(CapturedStmt, NormalizedStringStmt(statement=item))
        return cast(CapturedStmt, item)

    @property
    def queries_history(self) -> str:
        """
        Generates a copy-and-paste friendly string of all captured statements.

        This output translates internal session state into structured triple-quoted 
        string assertions. When debugging test failures, developers can inject this 
        property's output into their test code to rebuild their strict chronology 
        expectations visually rather than doing it manually.

        Returns:
            str: A meticulously formatted history of recorded queries and events.
        """
        out = []
        for raw_stmt in self.statements:
            stmt = self._normalize_statement(raw_stmt)
            formatted = f'"""\n{reformat_query(stmt.statement)}\n"""'
            if stmt.parameters is not None:
                formatted += f'\nParameters: {stmt.parameters}'
            out.append(formatted)
        return "\n\n".join(out)

    @property
    def help(self) -> str:
        """
        Provides debugging hints formatted with query history.

        Returns:
            str: Debugging output showing all statements recorded by this wrapper.
        """
        return f"Captured queries:\n{self.queries_history}"

    def assert_executed_queries(
        self,
        *expected_queries: Union[str, Tuple[str, Any]],
        strict: bool = True
    ) -> None:
        """
        Asserts that captured statements match an expected chronological sequence.

        This guarantees the absolute order, formatting, and parameter bound types 
        of every database command executed during the wrapped timeline.

        Users can define individual `expected_queries` items using two strict shapes:
        1. A raw `str` like `"BEGIN"` or an explicit pure query without parameters.
        2. A `Tuple[str, Any]` to match a specific executable query against 
           a precise boundary of parameters.

        Args:
            *expected_queries (Union[str, Tuple[str, Any]]): Variable length positional 
                arguments specifying the exact chronological sequence of queries.
            strict (bool): When True, forcefully ensures that the total number of expected
                queries equates to the total volume of queries captured inside the test run.
                Defaults to True.

        Raises:
            AssertionError: When sequence limits misalign, an executed query string shifts
                unexpectedly, or parameter states fail normalized assertion.
        """
        if strict:
            self.assert_total_queries(len(expected_queries))

        for i, expected in enumerate(expected_queries):
            if i >= len(self.statements):
                raise AssertionError(
                    f"Mismatch at index {i}\n"
                    f"Expected query or event but no more statements were recorded.\n\n"
                    f"{self.help}"
                )
                
            actual_stmt = self._normalize_statement(self.statements[i])
            actual_q_str = actual_stmt.statement
            actual_params = actual_stmt.parameters
            
            if isinstance(expected, tuple):
                expected_q_str, expected_params = expected
            else:
                expected_q_str, expected_params = expected, None

            expected_formatted = reformat_query(expected_q_str)
            actual_formatted = reformat_query(actual_q_str)
            
            if expected_formatted != actual_formatted:
                raise AssertionError(
                    f"Mismatch at index {i}\n"
                    f"Expected SQL:\n{expected_formatted}\n\n"
                    f"Actual SQL:\n{actual_formatted}\n\n"
                    f"{self.help}"
                )
            
            if expected_params is not None:
                norm_expected = _normalize_params(expected_params)
                norm_actual = _normalize_params(actual_params)
                if norm_expected != norm_actual:
                    raise AssertionError(
                        f"Mismatch at index {i}\n"
                        f"Expected Params:\n{expected_params}\n\n"
                        f"Actual Params:\n{actual_params}\n\n"
                        f"Normalized Context:\nExpected: {norm_expected}\nActual: {norm_actual}\n\n"
                        f"{self.help}"
                    )
            else:
                # Strictly enforce empty or None parameters for missing expectations
                if actual_params:
                    raise AssertionError(
                        f"Mismatch at index {i}\n"
                        f"Expected Params to be empty or None, but got:\n{actual_params}\n\n"
                        f"{self.help}"
                    )

    def assert_total_queries(self, expected_total_queries: int) -> None:
        """
        Asserts the absolute total count of queries and events fired.

        Args:
            expected_total_queries (int): The precise number of expected interactions.

        Raises:
            AssertionError: If actual executed interactions deviate from expectations.
        """
        if len(self.statements) != expected_total_queries:
            raise AssertionError(
                f"Expected {expected_total_queries} queries, but found {len(self.statements)}.\n\n{self.help}"
            )


@pytest.fixture
def capquery(sqlite_engine: Engine) -> CapQueryWrapper:
    """
    A pytest fixture yielding an active CapQueryWrapper across `sqlite_engine`.

    This simplifies asserting against database states within test cases by 
    intercepting execution instantly upon integration.

    Args:
        sqlite_engine (Engine): The underlying test database engine.

    Returns:
        CapQueryWrapper: A contextual interceptor handling the database session.
    """
    with CapQueryWrapper(sqlite_engine) as captured:
        yield captured