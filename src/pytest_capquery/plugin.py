import functools

import pytest
import sqlparse
from sqlalchemy_capture_sql import CaptureSqlStatements

format_query = functools.partial(sqlparse.format, reindent=True, keyword_case="upper")


def reformat_query(query: str) -> str:
    query = query.strip()
    parsed = sqlparse.parse(query)

    statements = [p for p in parsed if str(p).strip()]
    if len(statements) > 1:
        raise ValueError("Only one query is allowed.")

    return format_query(query)


class CapQueryWrapper(CaptureSqlStatements):
    @property
    def queries_history(self) -> str:
        """
        Reformats all captured statements and outputs them in a copy-and-paste
        friendly string format (triple quotes).
        """
        out = []
        for stmt in self.statements:
            q_str = str(getattr(stmt, "statement", stmt))
            out.append(f'"""\n{reformat_query(q_str)}\n"""')
        return "\n\n".join(out)

    @property
    def help(self) -> str:
        return f"Captured queries:\n{self.queries_history}"

    def assert_executed_queries(self, *expected_queries, has_commit=False, strict=True):
        executed_stmts = [str(getattr(stmt, "statement", stmt)) for stmt in self.statements]

        if strict:
            self.assert_total_queries(len(expected_queries))

        for i, expected in enumerate(expected_queries):
            if i < len(executed_stmts):
                expected_formatted = reformat_query(expected)
                actual_formatted = reformat_query(executed_stmts[i])
                assert expected_formatted == actual_formatted, self.help
            else:
                assert False, self.help

        if has_commit:
            self.assert_has_commit()

    def assert_total_queries(self, expected_total_queries: int):
        assert len(self.statements) == expected_total_queries, self.help

    def assert_has_commit(self):
        executed_stmts = [str(getattr(stmt, "statement", stmt)) for stmt in self.statements]
        assert any("RELEASE SAVEPOINT" in stmt for stmt in executed_stmts), self.help

    def assert_has_executed_query(self, expected_query: str):
        executed_stmts = [str(getattr(stmt, "statement", stmt)) for stmt in self.statements]
        expected_formatted = reformat_query(expected_query)
        assert any(expected_formatted == reformat_query(stmt) for stmt in executed_stmts), self.help


@pytest.fixture
def capquery(db_engine):
    with CapQueryWrapper(db_engine) as captured:
        yield captured