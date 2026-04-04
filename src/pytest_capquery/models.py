"""
Data models and typed protocol definitions for capture payloads.

This module provides the necessary runtime typing boundaries and data structures
required to accurately represent database transactional events intercepted
during SQLAlchemy execution tracking.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Sequence, Union, runtime_checkable


@runtime_checkable
class CapturedStmt(Protocol):
    """
    Protocol enforcing the required attributes of any captured statement payload.
    """
    @property
    def statement(self) -> str:
        """
        The raw string representation of the executed query or logical event.
        """
        ...

    @property
    def parameters(self) -> Any:
        """
        The dynamically bound parametric payload associated with the database execution.
        """
        ...


@dataclass
class TxEvent:
    """
    A structural data transfer object representing a discrete transaction event
    or query execution intercepted internally.
    """
    statement: str
    parameters: Optional[Union[Sequence[Any], Dict[str, Any]]] = None
    idx: int = field(init=False)
    duration: float = 0.0
    first_table: str = "N/A"
    sql_type: str = "EVENT"

    def __post_init__(self) -> None:
        """
        Lifecycle hook resolving specific unique instance boundaries mapping.
        """
        self.idx = id(self)

    def set_tst_next(self, now: Any) -> None:
        """
        Extension hook intended for timing capture integration logic resolving.
        """
        pass
