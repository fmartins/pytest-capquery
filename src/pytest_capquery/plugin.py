import functools
from typing import Any, Sequence, Tuple, Union, Optional, Dict, Callable, List

import pytest
import sqlparse
from sqlalchemy import event, Connection, Engine
from sqlalchemy_capture_sql import CaptureSqlStatements


format_query = functools.partial(sqlparse.format, reindent=True, keyword_case="upper")


def reformat_query(query: str) -> str:
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
    - Dicts: Sorted by key into a tuple of tuples.
    - Lists/Tuples: Converted to tuples, recursive normalization applied to elements.
    - Other types are left as-is.
    """
    if isinstance(params, dict):
        return tuple(sorted((k, _normalize_params(v)) for k, v in params.items()))
    elif isinstance(params, (list, tuple)):
        return tuple(_normalize_params(v) for v in params)
    return params


class TxEvent:
    """Wrapper for transaction events to match SQL statement structure."""
    def __init__(self, stmt: str) -> None:
        self.statement: str = stmt
        self.parameters: Optional[Union[Sequence[Any], Dict[str, Any]]] = None
        self.idx: int = id(self)
        self.duration: float = 0.0
        self.first_table: str = "N/A"
        self.sql_type: str = "EVENT"

    def set_tst_next(self, now: Any) -> None:
        pass


class CapQueryWrapper(CaptureSqlStatements):
    _listeners: Dict[str, Callable[[Connection], None]]

    def __enter__(self) -> "CapQueryWrapper":
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
        for name, fn in self._listeners.items():
            event.remove(self.engine, name, fn)
        super().__exit__(exc_type, exc_val, exc_tb)

    @property
    def queries_history(self) -> str:
        """
        Reformats all captured statements and outputs them in a copy-and-paste
        friendly string format (triple quotes).
        """
        out = []
        for stmt in self.statements:
            q_str = str(getattr(stmt, "statement", stmt))
            params = getattr(stmt, "parameters", None)
            formatted = f'"""\n{reformat_query(q_str)}\n"""'
            if params is not None:
                formatted += f'\nParameters: {params}'
            out.append(formatted)
        return "\n\n".join(out)

    @property
    def help(self) -> str:
        return f"Captured queries:\n{self.queries_history}"

    def assert_executed_queries(
        self,
        *expected_queries: Union[str, Tuple[str, Any]],
        strict: bool = True
    ) -> None:
        if strict:
            self.assert_total_queries(len(expected_queries))

        for i, expected in enumerate(expected_queries):
            if i >= len(self.statements):
                raise AssertionError(
                    f"Mismatch at index {i}\n"
                    f"Expected query or event but no more statements were recorded.\n\n"
                    f"{self.help}"
                )
                
            actual_stmt = self.statements[i]
            actual_q_str = str(getattr(actual_stmt, "statement", actual_stmt))
            actual_params = getattr(actual_stmt, "parameters", None)
            
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
        if len(self.statements) != expected_total_queries:
            raise AssertionError(
                f"Expected {expected_total_queries} queries, but found {len(self.statements)}.\n\n{self.help}"
            )


@pytest.fixture
def capquery(db_engine: Engine) -> CapQueryWrapper:
    with CapQueryWrapper(db_engine) as captured:
        yield captured