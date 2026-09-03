"""Simple CSS parser for terminal-mapped styles.

Supports parsing inline `style="..."` and very small stylesheet blocks like
`tag { prop: value; }` for tag selectors.
"""
from __future__ import annotations

import re
from typing import Dict


def parse_inline(style: str) -> Dict[str, str]:
    """Parse inline CSS style attribute."""
    props: Dict[str, str] = {}
    if not style:
        return props
    for part in style.split(";"):
        if not part.strip():
            continue
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k = k.strip().lower()
        v = v.strip()
        if k and v:
            props[k] = v
    return props


_RE_RULE = re.compile(r"([^{]+){([^}]+)}")
_RE_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def parse_stylesheet(css: str) -> Dict[str, Dict[str, str]]:
    """Parse a minimal stylesheet into tag -> {prop: val} map.

    Supports:
    - Simple tag selectors: `p`, `h1`, `a`
    - Class selectors: `.classname`
    - ID selectors: `#idname`
    - Element with class: `p.classname`
    - Compound selectors: `h1, h2, h3`
    """
    rules: Dict[str, Dict[str, str]] = {}
    if not css:
        return rules
    
    # Remove comments
    css = _RE_COMMENT.sub("", css)
    
    for m in _RE_RULE.finditer(css):
        selector = m.group(1).strip()
        body = m.group(2)
        props = parse_inline(body)
        
        # Handle comma-separated selectors
        for sel in selector.split(","):
            sel = sel.strip()
            if not sel:
                continue
            
            # Extract tag name (first part before . or #)
            tag = re.split(r'[.#\s]', sel)[0].strip().lower()
            
            if tag:
                rules.setdefault(tag, {}).update(props)
    
    return rules


def merge_styles(base: Dict[str, str], override: Dict[str, str]) -> Dict[str, str]:
    """Merge base styles with overrides."""
    result = dict(base)
    result.update(override)
    return result
