"""
Pytest Capquery Plugin.

License: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
Author: Felipe Cardoso Martins <felipe.cardoso.martins@gmail.com>

This module provides the core functionality for capturing and asserting upon
SQL statements executed via SQLAlchemy within pytest test cases.
"""

import ast
import functools
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence, Tuple, Union, Optional, Dict, Callable, List, cast, Protocol, runtime_checkable

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
    if isinstance(params, dict):
        return tuple(sorted((k, _normalize_params(v)) for k, v in params.items()))
    elif isinstance(params, (list, tuple)):
        return tuple(_normalize_params(v) for v in params)
    return params


@runtime_checkable
class CapturedStmt(Protocol):
    @property
    def statement(self) -> str: ...

    @property
    def parameters(self) -> Any: ...


@dataclass
class TxEvent:
    statement: str
    parameters: Optional[Union[Sequence[Any], Dict[str, Any]]] = None
    idx: int = field(init=False)
    duration: float = 0.0
    first_table: str = "N/A"
    sql_type: str = "EVENT"

    def __post_init__(self) -> None:
        self.idx = id(self)

    def set_tst_next(self, now: Any) -> None:
        pass


class SnapshotManager:
    def __init__(self, nodeid: str, test_path: Path, update_mode: bool):
        self.nodeid = nodeid
        self.update_mode = update_mode

        self.snapshot_dir = test_path.parent / "__capquery_snapshots__" / test_path.stem

        safe_name = nodeid.split("::")[-1].replace("[", "_").replace("]", "").replace("/", "_")
        self.snapshot_file = self.snapshot_dir / f"{safe_name}.sql"

    def save(self, content: str) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file.write_text(content, encoding="utf-8")

    def load(self) -> Optional[str]:
        if not self.snapshot_file.exists():
            return None
        return self.snapshot_file.read_text(encoding="utf-8")


class QueryAsserter:
    snapshot_manager: Optional[SnapshotManager] = None

    def _normalize_statement(self, item: Any) -> CapturedStmt:
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

    def assert_executed_queries(self, *expected_queries: Union[str, Tuple[str, Any]], strict: bool = True) -> None:
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
        if len(self.statements) != expected_total_queries:
            self._fail_with_instructions(
                f"Expected {expected_total_queries} queries, but found {len(self.statements)}.\n\n{self.help}"
            )


class CaptureContext(QueryAsserter):
    def __init__(self, wrapper: "CapQueryWrapper", expected_count: Optional[int] = None, assert_snapshot: bool = False, alias: Optional[str] = None) -> None:
        self._wrapper = wrapper
        self._expected_count = expected_count
        self._assert_snapshot = assert_snapshot
        self.alias = alias
        self.snapshot_manager = wrapper.snapshot_manager
        self._start_idx = 0
        self._end_idx = 0
        self._active = False
        self._phase_idx = 0

    def __enter__(self) -> "CaptureContext":
        self._start_idx = len(self._wrapper.statements)
        self._active = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._end_idx = len(self._wrapper.statements)
        self._active = False

        self._phase_idx = len(self._wrapper.phases)
        self._wrapper.phases.append({
            "alias": self.alias,
            "statements": self.statements
        })

        if exc_type is None and self._expected_count is not None:
            self.assert_total_queries(self._expected_count)
        if exc_type is None and self._assert_snapshot:
            self.assert_matches_snapshot()

    @property
    def statements(self) -> List[Any]:
        if self._active:
            return self._wrapper.statements[self._start_idx:]
        return self._wrapper.statements[self._start_idx:self._end_idx]

    def assert_matches_snapshot(self) -> None:
        if not self.snapshot_manager:
            raise RuntimeError("SnapshotManager is not configured. Ensure capquery fixture is used correctly.")

        if self.snapshot_manager.update_mode:
            content = self._wrapper._serialize_snapshot()
            self.snapshot_manager.save(content)
            return

        snapshot_content = self.snapshot_manager.load()

        if snapshot_content is None:
            raise AssertionError(
                f"No snapshot found for this test.\n"
                f"Run pytest with `--capquery-update` to generate it at:\n"
                f"{self.snapshot_manager.snapshot_file}"
            )

        all_expected_phases = self._wrapper._deserialize_snapshot(snapshot_content)

        if self._phase_idx >= len(all_expected_phases):
            raise AssertionError(f"Snapshot missing phase {self._phase_idx + 1}")

        expected_queries = all_expected_phases[self._phase_idx]
        self.assert_executed_queries(*expected_queries, strict=True)


class CapQueryWrapper(CaptureSqlStatements, QueryAsserter):
    _listeners: Dict[str, Callable[[Connection], None]]

    def __init__(self, engine: Engine, snapshot_manager: Optional[SnapshotManager] = None):
        super().__init__(engine)
        self.snapshot_manager = snapshot_manager
        self.phases: List[Dict[str, Any]] = []

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

    def capture(self, expected_count: Optional[int] = None, assert_snapshot: bool = False, alias: Optional[str] = None) -> CaptureContext:
        return CaptureContext(self, expected_count, assert_snapshot, alias)

    def _serialize_snapshot(self) -> str:
        lines = []
        query_counter = 1
        for phase_idx, phase in enumerate(self.phases, 1):
            alias = phase["alias"]
            alias_str = f" ({alias})" if alias else ""

            for raw_stmt in phase["statements"]:
                stmt = self._normalize_statement(raw_stmt)
                q_str = reformat_query(stmt.statement)
                if not q_str:
                    continue

                lines.append(f"-- CAPQUERY: Query {query_counter}")
                lines.append(f"-- EXPECTED_PARAMS: {repr(stmt.parameters)}")
                lines.append(f"-- PHASE: {phase_idx}{alias_str}")
                lines.append(q_str)
                lines.append("")
                query_counter += 1

        return "\n".join(lines).strip() + "\n"

    def _deserialize_snapshot(self, content: str) -> List[List[Union[str, Tuple[str, Any]]]]:
        phases: List[List[Union[str, Tuple[str, Any]]]] = []

        blocks = content.split("-- CAPQUERY:")
        for block in blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            params_str = "None"
            phase_num = 1
            query_lines = []

            for line in lines[1:]:
                if line.startswith("-- EXPECTED_PARAMS:"):
                    params_str = line.replace("-- EXPECTED_PARAMS:", "").strip()
                elif line.startswith("-- PHASE:"):
                    phase_info = line.replace("-- PHASE:", "").strip()
                    phase_num = int(phase_info.split()[0])
                else:
                    query_lines.append(line)

            query_str = "\n".join(query_lines).strip()
            if not query_str:
                continue

            params = ast.literal_eval(params_str)
            item = query_str if params is None else (query_str, params)

            while len(phases) < phase_num:
                phases.append([])

            phases[phase_num - 1].append(item)

        return phases


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("capquery", "SQLAlchemy Query Assertions")
    group.addoption(
        "--capquery-update",
        action="store_true",
        default=False,
        help="Update capquery .sql snapshot files instead of failing tests."
    )


@pytest.fixture
def capquery(request: pytest.FixtureRequest, sqlite_engine: Engine) -> CapQueryWrapper:
    update_mode = request.config.getoption("--capquery-update")
    snapshot_manager = SnapshotManager(
        nodeid=request.node.nodeid,
        test_path=Path(request.node.path),
        update_mode=update_mode
    )

    with CapQueryWrapper(sqlite_engine, snapshot_manager=snapshot_manager) as captured:
        yield captured
