import functools

import pytest
import sqlparse
from sqlalchemy import event
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


class TxEvent:
    def __init__(self, stmt):
        self.statement = stmt
        self.parameters = None
        self.idx = id(self)
        self.duration = 0.0
        self.first_table = "N/A"
        self.sql_type = "EVENT"
    
    def set_tst_next(self, now):
        pass


class CapQueryWrapper(CaptureSqlStatements):
    def __enter__(self):
        super().__enter__()
        
        self._listeners = {
            'begin': lambda c: self.statements.append(TxEvent("BEGIN")),
            'commit': lambda c: self.statements.append(TxEvent("COMMIT")),
            'rollback': lambda c: self.statements.append(TxEvent("ROLLBACK")),
        }
        for name, fn in self._listeners.items():
            event.listen(self.engine, name, fn)
            
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for name, fn in self._listeners.items():
            event.remove(self.engine, name, fn)
        return super().__exit__(exc_type, exc_val, exc_tb)

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

    def assert_executed_queries(self, *expected_queries, has_commit=False, strict=True):
        if strict:
            self.assert_total_queries(len(expected_queries))

        for i, expected in enumerate(expected_queries):
            if i >= len(self.statements):
                assert False, self.help
                
            actual_stmt = self.statements[i]
            actual_q_str = str(getattr(actual_stmt, "statement", actual_stmt))
            
            if isinstance(expected, tuple):
                expected_q_str, expected_params = expected
            else:
                expected_q_str, expected_params = expected, None

            expected_formatted = reformat_query(expected_q_str)
            actual_formatted = reformat_query(actual_q_str)
            assert expected_formatted == actual_formatted, self.help
            
            if expected_params is not None:
                actual_params = getattr(actual_stmt, "parameters", None)
                assert expected_params == actual_params, self.help

        if has_commit:
            self.assert_has_commit()

    def assert_total_queries(self, expected_total_queries: int):
        assert len(self.statements) == expected_total_queries, self.help

    def assert_has_begin(self):
        executed_stmts = [str(getattr(stmt, "statement", stmt)).strip().upper() for stmt in self.statements]
        assert any(stmt == "BEGIN" for stmt in executed_stmts), self.help

    def assert_has_commit(self):
        executed_stmts = [str(getattr(stmt, "statement", stmt)).strip().upper() for stmt in self.statements]
        assert any(stmt == "COMMIT" for stmt in executed_stmts), self.help

    def assert_has_rollback(self):
        executed_stmts = [str(getattr(stmt, "statement", stmt)).strip().upper() for stmt in self.statements]
        assert any(stmt == "ROLLBACK" for stmt in executed_stmts), self.help

    def assert_has_no_commit(self):
        executed_stmts = [str(getattr(stmt, "statement", stmt)).strip().upper() for stmt in self.statements]
        assert not any(stmt == "COMMIT" for stmt in executed_stmts), self.help

    def assert_has_executed_query(self, expected_query: str, expected_params=None):
        expected_formatted = reformat_query(expected_query)
        for stmt in self.statements:
            stmt_query = str(getattr(stmt, "statement", stmt))
            if expected_formatted == reformat_query(stmt_query):
                if expected_params is not None:
                    if getattr(stmt, "parameters", None) == expected_params:
                        return
                    continue
                return
        assert False, self.help


@pytest.fixture
def capquery(db_engine):
    with CapQueryWrapper(db_engine) as captured:
        yield captured