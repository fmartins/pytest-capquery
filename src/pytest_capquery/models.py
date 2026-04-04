"""
Models.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Sequence, Union, runtime_checkable


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
