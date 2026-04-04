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
import sys
import textwrap
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
    duration: float = 0.0
    first_table: str = "N/A"
    sql_type: str = "STATEMENT"
    idx: int = 0

    def __post_init__(self) -> None:
        # Give it a unique ID to satisfy the base class's SQLite insertion
        self.idx = id(self)

    def set_tst_next(self, now: Any) -> None:
        """
        Hook used by sqlalchemy-capture-sql for tracking timestamps
        between subsequent events.
        """
        pass


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


class QueryAsserter:
    """
    Base mixin providing assertion capabilities and formatting over a collection of SQL statements.
    """

    def _normalize_statement(self, item: Any) -> CapturedStmt:
        """
        Internally coerces parsed statements into the CapturedStmt protocol.

        Args:
            item (Any): Raw output appended to statements.

        Returns:
            CapturedStmt: The safely typed object with .statement and .parameters access.
        """
        return cast(CapturedStmt, item)

    @property
    def copy_paste_block(self) -> str:
        lines = []
        for raw_stmt in self.statements:
            stmt = self._normalize_statement(raw_stmt)
            q_str = reformat_query(stmt.statement)

            if not q_str:
                continue

            if "\n" not in q_str and len(q_str) < 30 and stmt.parameters is None:
                lines.append(f'    "{q_str}"')
                continue

            indented_sql = textwrap.indent(q_str, "        ")

            if stmt.parameters is not None:
                lines.append(
                    "    (\n"
                    "        # language=SQL\n"
                    '        """\n'
                    f"{indented_sql}\n"
                    '        """,\n'
                    f"        {repr(stmt.parameters)}\n"
                    "    )"
                )
            else:
                lines.append(
                    "    # language=SQL\n"
                    '    """\n'
                    f"{indented_sql}\n"
                    '    """'
                )

        joined_blocks = ",\n".join(lines)
        return f"assert_executed_queries(\n{joined_blocks}\n)"

    @property
    def queries_history(self) -> str:
        """
        Generates a copy-and-paste friendly string of all captured statements.

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

    def _fail_with_instructions(self, error_msg: str) -> None:
        divider = "=" * 80
        out = (
            f"\n{divider}\n"
            f"🚨 CAPQUERY: COPY & PASTE TO FIX ASSERTION 🚨\n"
            f"{divider}\n\n"
            f"{self.copy_paste_block}\n\n"
            f"{divider}\n"
        )
        sys.stdout.write(out)
        sys.stdout.flush()
        raise AssertionError(f"{error_msg}\n\n(See 'Captured stdout call' above for the copy-paste block)")

    def assert_executed_queries(
        self,
        *expected_queries: Union[str, Tuple[str, Any]],
        strict: bool = True
    ) -> None:
        """
        Asserts that captured statements match an expected chronological sequence.

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
                self._fail_with_instructions(
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
                self._fail_with_instructions(
                    f"Mismatch at index {i}\n"
                    f"Expected SQL:\n{expected_formatted}\n\n"
                    f"Actual SQL:\n{actual_formatted}\n\n"
                    f"{self.help}"
                )

            if expected_params is not None:
                norm_expected = _normalize_params(expected_params)
                norm_actual = _normalize_params(actual_params)
                if norm_expected != norm_actual:
                    self._fail_with_instructions(
                        f"Mismatch at index {i}\n"
                        f"Expected Params:\n{expected_params}\n\n"
                        f"Actual Params:\n{actual_params}\n\n"
                        f"Normalized Context:\nExpected: {norm_expected}\nActual: {norm_actual}\n\n"
                        f"{self.help}"
                    )
            else:
                if actual_params:
                    self._fail_with_instructions(
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
            self._fail_with_instructions(
                f"Expected {expected_total_queries} queries, but found {len(self.statements)}.\n\n{self.help}"
            )


class CaptureContext(QueryAsserter):
    """
    A context manager representing a localized slice of captured SQL queries.
    """
    def __init__(self, wrapper: "CapQueryWrapper", expected_count: Optional[int] = None) -> None:
        """
        Initializes a new capture context.

        Args:
            wrapper (CapQueryWrapper): The parent wrapper capturing global statements.
            expected_count (Optional[int]): The strictly expected number of queries to assert on exit.
        """
        self._wrapper = wrapper
        self._expected_count = expected_count
        self._start_idx = 0
        self._end_idx = 0
        self._active = False

    def __enter__(self) -> "CaptureContext":
        """
        Enters the context manager and anchors the starting index.

        Returns:
            CaptureContext: The active capture context.
        """
        self._start_idx = len(self._wrapper.statements)
        self._active = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exits the context manager, anchors the ending index, and asserts total queries if expected.
        """
        self._end_idx = len(self._wrapper.statements)
        self._active = False
        if exc_type is None and self._expected_count is not None:
            self.assert_total_queries(self._expected_count)

    @property
    def statements(self) -> List[Any]:
        """
        Retrieves the slice of statements captured during the lifecycle of this context.

        Returns:
            List[Any]: The isolated segment of executed queries.
        """
        if self._active:
            return self._wrapper.statements[self._start_idx:]
        return self._wrapper.statements[self._start_idx:self._end_idx]


class CapQueryWrapper(CaptureSqlStatements, QueryAsserter):
    """
    A context manager and SQLAlchemy event listener for capturing executed queries.

    This class runs at the boundary of SQLAlchemy engines, intercepting query
    events in real time while pushing explicit transaction logs (BEGIN, COMMIT)
    into a unified collection timeline.
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

    def capture(self, expected_count: Optional[int] = None) -> CaptureContext:
        """
        Creates a localized capture context to isolate a specific timeline of queries.

        Args:
            expected_count (Optional[int]): The strictly expected number of queries executed inside the block.

        Returns:
            CaptureContext: A context manager exposing only the localized slice of the execution timeline.
        """
        return CaptureContext(self, expected_count)


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
