# src/holdem/io/__init__.py
"""Input/Output: CLI entrypoint and hand-history writers."""

from __future__ import annotations
from typing import TYPE_CHECKING

__all__ = [
    # "main",
    # "HHWriter",
    # "HandHistoryWriter"
]

if TYPE_CHECKING:  # pragma: no cover
    # from .cli import main as main
    # from .hh_writer import HHWriter as HHWriter
    pass

# Lazy attribute access so importing `holdem.io` doesn't pull CLI deps immediately.
def __getattr__(name: str):
    if name == "main":
        from .cli import main  # noqa: WPS433 (local import for laziness)
        return main
    if name in ("HHWriter", "HandHistoryWriter"):
        from .hh_writer import HHWriter  # noqa: WPS433
        return HHWriter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__():
    return sorted(__all__)