"""Safe JavaScript execution abstraction.

The default engine is intentionally inert. Webpage scripts must never receive
Python objects, filesystem access, or unrestricted host callbacks.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


class JavaScriptEngine(ABC):
    """Interface for a future sandboxed JavaScript runtime."""

    @abstractmethod
    def execute(self, script: str) -> Any:
        """Execute a script under the engine's security policy."""

    @abstractmethod
    def set_dom_value(self, selector: str, value: str) -> None:
        """Expose a deliberately narrow DOM mutation operation."""


@dataclass
class NullJavaScriptEngine(JavaScriptEngine):
    """Safe default that reports scripts as unsupported and does nothing."""

    events: list[str] = field(default_factory=list)

    def execute(self, script: str) -> dict[str, str]:
        self.events.append("script skipped")
        return {"status": "unsupported", "reason": "No JavaScript runtime configured"}

    def set_dom_value(self, selector: str, value: str) -> None:
        self.events.append(f"DOM mutation skipped: {selector}")


def create_javascript_engine(enabled: bool = False) -> JavaScriptEngine:
    """Return the inert engine unless an explicit safe backend is configured."""
    if not enabled:
        return NullJavaScriptEngine()
    try:
        import quickjs  # type: ignore  # optional dependency
    except ImportError:
        return NullJavaScriptEngine()
    return NullJavaScriptEngine()
