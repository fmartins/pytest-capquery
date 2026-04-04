"""
Pytest Capquery Plugin.

License: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
Author: Felipe Cardoso Martins <felipe.cardoso.martins@gmail.com>

This module hooks into SQLAlchemy event loops orchestrating the translation
between execution logs over to assertions models natively surfacing the capquery local features.
"""

import ast
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pytest
from sqlalchemy import Connection, Engine, event
from sqlalchemy_capture_sql import CaptureSqlStatements

from pytest_capquery.asserter import CaptureContext, QueryAsserter
from pytest_capquery.formatter import reformat_query
from pytest_capquery.models import TxEvent
from pytest_capquery.snapshot import SnapshotManager


class CapQueryWrapper(CaptureSqlStatements, QueryAsserter):
    """
    The principal orchestration block bridging standard intercept hooks tightly onto
    internal verification ledgers. Translates database connection signals actively
    and provisions isolated context managers.
    """
    _listeners: Dict[str, Callable[[Connection], None]]

    def __init__(self, engine: Engine, snapshot_manager: Optional[SnapshotManager] = None) -> None:
        """
        Instantiates wrapper payload collections against the provided SQLAlchemy Engine.
        """
        super().__init__(engine)
        self.snapshot_manager = snapshot_manager
        self.phases: List[Dict[str, Any]] = []

    def __enter__(self) -> "CapQueryWrapper":
        """
        Registers core lifecycle event traps establishing tracking footprints seamlessly.
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
        Cleans dynamically wired framework event traps ensuring pristine un-contaminated exits.
        """
        for name, fn in self._listeners.items():
            event.remove(self.engine, name, fn)
        super().__exit__(exc_type, exc_val, exc_tb)

    def capture(self, expected_count: Optional[int] = None, assert_snapshot: bool = False, alias: Optional[str] = None) -> CaptureContext:
        """
        Generates and scopes a distinctly detached logic block delegating boundary mapping
        while pushing results toward the standard sequential ledger seamlessly.
        """
        return CaptureContext(self, expected_count, assert_snapshot, alias)

    def _serialize_snapshot(self) -> str:
        """
        Translates raw parameter maps and SQL blocks logically into explicitly formed disk
        persistence definitions.
        """
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
        """
        Navigates disk strings reversing parameter definitions directly up toward standard
        internal comparative models properly handling sequence parsing cleanly.
        """
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
    """
    Extends the native testing client bridging explicitly required execution arguments.
    """
    group = parser.getgroup("capquery", "SQLAlchemy Query Assertions")
    group.addoption(
        "--capquery-update",
        action="store_true",
        default=False,
        help="Update capquery .sql snapshot files instead of failing tests."
    )


@pytest.fixture
def capquery(request: pytest.FixtureRequest, sqlite_engine: Engine) -> CapQueryWrapper:
    """
    High-level standard testing interface securely delivering functional interception wrappers.
    This fixture is specifically configured natively defaulting to standard SQLite validation.
    """
    update_mode = request.config.getoption("--capquery-update")
    snapshot_manager = SnapshotManager(
        nodeid=request.node.nodeid,
        test_path=Path(request.node.path),
        update_mode=update_mode
    )

    with CapQueryWrapper(sqlite_engine, snapshot_manager=snapshot_manager) as captured:
        yield captured
