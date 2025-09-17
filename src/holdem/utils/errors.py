# src/holdem/utils/errors.py
from __future__ import annotations
from dataclasses import dataclass

__all__ = ["TableStateError", "PotsStateError", "EngineStateError"]

@dataclass(eq=False)
class TableStateError(RuntimeError):
    msg: str

    def __str__(self) -> str:
        return self.msg

@dataclass(eq=False)
class PotsStateError(ValueError):
    msg: str

    def __str__(self) -> str:
        return self.msg

@dataclass(eq=False)
class EngineStateError(ValueError):
    msg: str

    def __str__(self) -> str:
        return self.msg
