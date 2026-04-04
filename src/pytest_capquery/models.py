"""Data models and typed protocol definitions for capture payloads.

This module provides the necessary runtime typing boundaries and data structures required to
accurately represent database transactional events intercepted during SQLAlchemy execution tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Protocol, Sequence, Union, runtime_checkable

SqlParams = Optional[Union[Sequence[object], Dict[str, object]]]


@runtime_checkable
class CapturedStmt(Protocol):
    """Protocol enforcing the required attributes of any captured statement payload."""

    @property
    def statement(self) -> str:
        """The raw string representation of the executed query or logical event.

        Returns:
            str: The literal strings or events triggered at the connection level.
        """
        ...

    @property
    def parameters(self) -> SqlParams:
        """The dynamically bound parametric payload associated with the database execution.

        Returns:
            SqlParams: The parameterized arguments passed synchronously to the database driver.
        """
        ...


@dataclass
class TxEvent:
    """A structural data transfer object representing a discrete transaction event or query
    execution intercepted internally."""

    statement: str
    parameters: SqlParams = None
    idx: int = field(init=False)
    duration: float = 0.0
    first_table: str = "N/A"
    sql_type: str = "EVENT"

    def __post_init__(self) -> None:
        """Lifecycle hook resolving specific unique instance boundaries mapping.

        Returns:
            None
        """
        self.idx = id(self)

    def set_tst_next(self, now: float) -> None:
        """Extension hook intended for timing capture integration logic resolving.

        Args:
            now (float): Unix epoch float timestamp matching standard completion metrics.

        Returns:
            None
        """
        pass
