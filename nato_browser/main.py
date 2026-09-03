"""NATO ASCII Browser - Phase 1 CLI entrypoint

Phase 1: URL fetching + HTML parsing + paragraphs/headings/links.
"""
from __future__ import annotations

import sys
import textwrap
from urllib.parse import urljoin, urlparse

from nato_browser.network.http import fetch
from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom
from nato_browser.html.dom import Element, Text

# Prefer TUI if available
def run_ui(initial_url: str | None = None, ui_type: str = "textual"):
    """Run the browser with specified UI backend (textual or tkinter)."""
    if ui_type == "cli":
        return False
    if ui_type == "tkinter":
        try:
            from nato_browser.ui.tkinter_app import NatoTkinterApp

            app = NatoTkinterApp(initial_url=initial_url or "https://example.com")
            app.run()
            return True
        except Exception as e:
            print(f"Tkinter UI failed: {e}")
            return False
    else:  # default to textual
        try:
            from nato_browser.ui.app import NatoApp

            app = NatoApp(initial_url=initial_url)
            app.run()
            return True
        except Exception:
            return False


def run_tui(initial_url: str | None = None):
    """Run with Textual TUI (legacy interface)."""
    return run_ui(initial_url, ui_type="textual")


class SimpleBrowser:
    def __init__(self):
        self.history: list[str] = []
        self.index = -1

    def navigate(self, url: str, push_history: bool = True):
        url = self._normalize_url(url)
        print(f"Loading: {url}")
        final_url, html, headers, status = fetch(url)
        if status == 0:
            print(f"Failed to load {url} (request timed out or failed)")
            return [], url
        builder = DOMBuilder()
        builder.feed(html)
        dom = builder.root
        title = ""
        # try to find title
        for c in builder.root.children:
            if isinstance(c, Element) and c.tag == "head":
                for cc in c.children:
                    if isinstance(cc, Element) and cc.tag == "title":
                        title = " ".join([t.data for t in cc.children if isinstance(t, Text)])
                        break

        width = 80
        rendered, links, controls = render_dom(dom, width=width)

        header = f"{title or final_url}\n{'='*min(width, len(title or final_url))}\n"
        print("\n" + header + rendered)
        if links:
            print("\nLinks:")
            for i, href, text in links:
                print(f"  [{i}] {text} -> {href}")

        if push_history:
            # trim forward history
            if self.index < len(self.history) - 1:
                self.history = self.history[: self.index + 1]
            self.history.append(final_url)
            self.index = len(self.history) - 1

        return links, final_url

    def _normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url:
            return url
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
        return url

    def back(self):
        if self.index > 0:
            self.index -= 1
            return self.history[self.index]

    def forward(self):
        if self.index < len(self.history) - 1:
            self.index += 1
            return self.history[self.index]


def run(initial_url: str | None = None, ui_type: str = "textual"):
    """Run the browser with specified UI type."""
    # Try launching specified UI first
    if run_ui(initial_url, ui_type=ui_type):
        return

    # Fallback to simple CLI browser
    browser = SimpleBrowser()

    if initial_url:
        links, current = browser.navigate(initial_url)
    else:
        links, current = [], None

    while True:
        try:
            cmd = input("\nCommand (enter link number, u=url, b=back, f=forward, r=reload, q=quit): ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        cmd = cmd.strip()
        if not cmd:
            continue
        if cmd.lower() == "q":
            break
        if cmd.lower() == "b":
            url = browser.back()
            if url:
                links, current = browser.navigate(url, push_history=False)
            else:
                print("No back history")
            continue
        if cmd.lower() == "f":
            url = browser.forward()
            if url:
                links, current = browser.navigate(url, push_history=False)
            else:
                print("No forward history")
            continue
        if cmd.lower() == "r":
            if current:
                links, current = browser.navigate(current, push_history=False)
            else:
                print("No page to reload")
            continue
        if cmd.lower().startswith("u="):
            url = cmd[2:].strip()
            links, current = browser.navigate(url)
            continue

        # numeric link selection
        if cmd.isdigit():
            idx = int(cmd)
            match = [l for l in links if l[0] == idx]
            if match:
                _, href, _ = match[0]
                # resolve relative
                resolved = urljoin(current or "", href)
                links, current = browser.navigate(resolved)
            else:
                print("Invalid link number")
            continue

        # otherwise assume it's a URL
        links, current = browser.navigate(cmd)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NATO ASCII Browser")
    parser.add_argument("url", nargs="?", default=None, help="Initial URL to load")
    parser.add_argument("--ui", choices=["textual", "tkinter", "cli"], default="textual", help="UI backend to use")
    
    args = parser.parse_args()
    run(args.url, ui_type=args.ui)


# Convenience functions for console entry points
def run_default():
    """Default entry point (textual TUI)."""
    import argparse
    parser = argparse.ArgumentParser(description="NATO ASCII Browser")
    parser.add_argument("url", nargs="?", default="https://example.com", help="Initial URL to load")
    parser.add_argument("--ui", choices=["textual", "tkinter"], default="textual", help="UI backend to use")
    args = parser.parse_args()
    run(args.url, ui_type=args.ui)


def run_textual():
    """TUI entry point (Textual)."""
    import argparse
    parser = argparse.ArgumentParser(description="NATO ASCII Browser (TUI)")
    parser.add_argument("url", nargs="?", default="https://example.com", help="Initial URL to load")
    args = parser.parse_args()
    run(args.url, ui_type="textual")


def run_tkinter():
    """GUI entry point (Tkinter)."""
    import argparse
    parser = argparse.ArgumentParser(description="NATO ASCII Browser (GUI)")
    parser.add_argument("url", nargs="?", default="https://example.com", help="Initial URL to load")
    args = parser.parse_args()
    run(args.url, ui_type="tkinter")
