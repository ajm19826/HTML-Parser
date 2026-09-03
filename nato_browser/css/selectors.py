"""Small, deterministic CSS selector matcher for the terminal renderer."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List

from nato_browser.css.parser import parse_inline
from nato_browser.html.dom import Element


@dataclass(frozen=True)
class CSSRule:
    selector: str
    properties: Dict[str, str]
    specificity: tuple[int, int, int]
    order: int


def _specificity(selector: str) -> tuple[int, int, int]:
    return (
        len(re.findall(r"#[A-Za-z_][\w-]*", selector)),
        len(re.findall(r"\.[A-Za-z_][\w-]*", selector)),
        len(re.findall(r"(?:^|[ >])([A-Za-z][\w-]*)", selector)),
    )


def parse_rules(css: str) -> List[CSSRule]:
    """Parse simple CSS rules while preserving selector specificity and order."""
    from nato_browser.css.parser import _RE_COMMENT, _RE_RULE

    rules: List[CSSRule] = []
    css = _RE_COMMENT.sub("", css or "")
    order = 0
    for match in _RE_RULE.finditer(css):
        properties = parse_inline(match.group(2))
        for selector in match.group(1).split(","):
            selector = selector.strip()
            if selector:
                rules.append(CSSRule(selector, properties, _specificity(selector), order))
                order += 1
    return rules


def _matches_compound(element: Element, compound: str) -> bool:
    if compound == "*":
        return True
    tag_match = re.match(r"^[A-Za-z][\w-]*", compound)
    if tag_match and element.tag != tag_match.group(0).lower():
        return False
    for element_id in re.findall(r"#([\w-]+)", compound):
        if (element.attrs or {}).get("id", "") != element_id:
            return False
    classes = set((element.attrs or {}).get("class", "").split())
    return all(class_name in classes for class_name in re.findall(r"\.([\w-]+)", compound))


def _tokens(selector: str) -> List[str]:
    return re.findall(r"[^\s>]+|>", selector.strip())


def matches(element: Element, selector: str) -> bool:
    """Match element, class, ID, descendant, and child selectors."""
    tokens = _tokens(selector)
    if not tokens or tokens[-1] == ">":
        return False
    current: Element | None = element
    index = len(tokens) - 1
    if not _matches_compound(current, tokens[index]):
        return False
    index -= 1
    while index >= 0:
        relation = " "
        if tokens[index] == ">":
            relation = ">"
            index -= 1
        if index < 0 or current is None:
            return False
        compound = tokens[index]
        index -= 1
        if relation == ">":
            parent = current.parent
            if parent is None or not _matches_compound(parent, compound):
                return False
            current = parent
        else:
            parent = current.parent
            while parent is not None and not _matches_compound(parent, compound):
                parent = parent.parent
            if parent is None:
                return False
            current = parent
    return True


def compute_style_for_element(element: Element, rules: Iterable[CSSRule]) -> Dict[str, str]:
    """Apply matching rules with CSS-like priority, then inline declarations."""
    selected: Dict[str, tuple[bool, tuple[int, int, int], int, str]] = {}
    for rule in rules:
        if not matches(element, rule.selector):
            continue
        for property_name, raw_value in rule.properties.items():
            important = raw_value.lower().endswith("!important")
            value = raw_value[:-10].strip() if important else raw_value
            candidate = (important, rule.specificity, rule.order, value)
            previous = selected.get(property_name)
            if previous is None or candidate[:3] >= previous[:3]:
                selected[property_name] = candidate

    style = {name: candidate[3] for name, candidate in selected.items()}
    inline = parse_inline((element.attrs or {}).get("style", ""))
    for property_name, raw_value in inline.items():
        important = raw_value.lower().endswith("!important")
        value = raw_value[:-10].strip() if important else raw_value
        previous = selected.get(property_name)
        if important or previous is None or not previous[0]:
            style[property_name] = value
    return style
