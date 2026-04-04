"""
Asserter.
"""
import sys
import textwrap
from typing import Any, List, Optional, Tuple, Union, cast

from pytest_capquery.formatter import normalize_params, reformat_query
from pytest_capquery.models import CapturedStmt
from pytest_capquery.snapshot import SnapshotManager


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
                norm_expected = normalize_params(expected_params)
                norm_actual = normalize_params(actual_params)
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
    def __init__(self, wrapper: Any, expected_count: Optional[int] = None, assert_snapshot: bool = False, alias: Optional[str] = None) -> None:
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
