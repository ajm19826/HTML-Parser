"""DOM node classes for a lightweight HTML DOM."""
from __future__ import annotations

from typing import List, Dict, Optional


class Node:
    def __init__(self):
        self.parent: Optional[Element] = None


class Text(Node):
    def __init__(self, data: str):
        super().__init__()
        self.data = data

    def __repr__(self):
        return f"Text({self.data!r})"


class Element(Node):
    def __init__(self, tag: str, attrs: Dict[str, str] | None = None):
        super().__init__()
        self.tag = tag.lower()
        self.attrs = attrs or {}
        self.children: List[Node] = []

    def append(self, node: Node):
        node.parent = self
        self.children.append(node)

    def __repr__(self):
        return f"Element({self.tag}, attrs={self.attrs}, children={len(self.children)})"
