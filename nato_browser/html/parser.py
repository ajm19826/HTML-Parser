"""Build a simple DOM tree using html.parser.HTMLParser."""
from __future__ import annotations

from html.parser import HTMLParser
from typing import List, Tuple

from nato_browser.html.dom import Element, Text


class DOMBuilder(HTMLParser):
    # Extended list of self-closing tags (HTML5)
    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "keygen", "link", "meta", "param", "source", "track", "wbr"
    }
    OPTIONAL_END_TAGS = {
        "p": {"p", "div", "section", "article", "header", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table"},
        "li": {"li"},
        "dt": {"dt", "dd"},
        "dd": {"dt", "dd"},
        "tr": {"tr"},
        "td": {"td", "th"},
        "th": {"td", "th"},
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("html")
        self.stack: List[Element] = [self.root]
        self.error_recovery = True

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        tag_lower = tag.lower()
        attrdict = {k: (v if v is not None else "") for k, v in attrs if k}

        # Recover the implicit closing tags commonly omitted in HTML.
        while len(self.stack) > 1:
            open_tag = self.stack[-1].tag
            if tag_lower not in self.OPTIONAL_END_TAGS.get(open_tag, set()):
                break
            self.stack.pop()

        el = Element(tag_lower, attrdict)
        
        if self.stack:
            self.stack[-1].append(el)
        
        # Void elements (self-closing) should not be pushed to stack
        if tag_lower not in self.VOID_TAGS:
            self.stack.append(el)

    def handle_endtag(self, tag: str):
        """Handle closing tags with robustness to unbalanced markup."""
        tag_lower = tag.lower()
        
        # Don't try to pop void tags
        if tag_lower in self.VOID_TAGS:
            return
        
        # Pop until matching tag (robust to unbalanced tags)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag_lower:
                self.stack = self.stack[:i]
                return
        
        # If tag not found in stack, just ignore (unbalanced markup)

    def handle_startendtag(self, tag: str, attrs):
        """Handle self-closing tags."""
        tag_lower = tag.lower()
        attrdict = {k: (v if v is not None else "") for k, v in attrs if k}
        el = Element(tag_lower, attrdict)
        if self.stack:
            self.stack[-1].append(el)

    def handle_data(self, data: str):
        """Handle text data with whitespace preservation for pre/code."""
        if not self.stack:
            return
        
        parent_tag = self.stack[-1].tag
        
        # Preserve whitespace in pre, code, script, style
        if parent_tag in ("pre", "code", "script", "style"):
            text = data
        else:
            # Collapse multiple whitespace to single space
            text = " ".join(data.split())
        
        if not text:
            return
        
        node = Text(text)
        self.stack[-1].append(node)

    def handle_comment(self, data: str):
        """Ignore HTML comments."""
        pass

    def handle_decl(self, decl: str):
        """Ignore doctype and other declarations."""
        pass

    def feed(self, data: str):
        """Override feed to handle encoding issues gracefully."""
        try:
            super().feed(data)
        except Exception:
            # If parsing fails, try with errors='ignore'
            try:
                if isinstance(data, bytes):
                    data = data.decode(errors='ignore')
                super().feed(data)
            except Exception:
                # Last resort: use raw data as-is
                pass
