"""Small shared diagnostics store for DOM, CSS, network, media, and console data."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from nato_browser.html.dom import Element, Text


@dataclass
class DebugSession:
    network: list[dict[str, Any]] = field(default_factory=list)
    media: list[dict[str, Any]] = field(default_factory=list)
    console: list[str] = field(default_factory=list)
    dom: str = ""
    css: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add_network(self, **entry: Any) -> None:
        with self._lock:
            self.network.append(entry)
            del self.network[:-100]

    def add_console(self, message: str) -> None:
        with self._lock:
            self.console.append(message)
            del self.console[:-100]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"network": list(self.network), "media": list(self.media), "console": list(self.console), "dom": self.dom, "css": list(self.css)}


debug_session = DebugSession()


def format_dom_tree(root: Element) -> str:
    """Return a compact tree suitable for a terminal diagnostics panel."""
    lines: list[str] = []

    def visit(node: Element, prefix: str = "", is_last: bool = True) -> None:
        branch = "└── " if is_last else "├── "
        lines.append(prefix + branch + node.tag)
        children = [child for child in node.children if isinstance(child, Element)]
        for index, child in enumerate(children):
            visit(child, prefix + ("    " if is_last else "│   "), index == len(children) - 1)

    visit(root)
    return "\n".join(lines)
