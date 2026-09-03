"""Compute computed styles for DOM elements with simple defaults."""
from __future__ import annotations

from typing import Dict

INLINE_ELEMENTS = {
    "a",
    "span",
    "b",
    "strong",
    "em",
    "i",
    "u",
    "code",
    "img",
}

BLOCK_ELEMENTS = {
    "div",
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "table",
    "tr",
    "td",
    "th",
    "header",
    "footer",
    "main",
    "section",
}


def compute_style(tag: str, inline: Dict[str, str], tag_rules: Dict[str, str]) -> Dict[str, str]:
    """Return a computed style dict for an element.

    Rules: tag_rules (from stylesheet) are applied first, then inline overrides.
    Provide minimal defaults: display, font-weight defaulting to normal, text-align left.
    """
    style: Dict[str, str] = {}
    # start with tag rules
    if tag_rules:
        style.update(tag_rules)
    # then inline
    if inline:
        style.update(inline)

    # defaults
    if "display" not in style:
        if tag in INLINE_ELEMENTS:
            style["display"] = "inline"
        elif tag in BLOCK_ELEMENTS:
            style["display"] = "block"
        else:
            style["display"] = "block"

    if "text-align" not in style:
        style["text-align"] = "left"

    if "font-weight" not in style:
        style["font-weight"] = "normal"

    # normalize margin/padding numeric values if present like '10px' -> int
    for prop in ("margin", "margin-top", "margin-bottom", "padding-left", "padding-right"):
        v = style.get(prop)
        if v:
            try:
                if v.endswith("px"):
                    style[prop] = str(int(v[:-2]))
                else:
                    style[prop] = str(int(v))
            except Exception:
                # leave as-is
                pass

    return style
