"""NATO ASCII Browser - main entry point for module execution."""
from __future__ import annotations

import sys
import argparse
import logging
import os

from nato_browser.main import run


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NATO ASCII Browser - Browse the web in your terminal",
        prog="nato-browser"
    )
    parser.add_argument("url", nargs="?", default="https://example.com", help="Initial URL to load (default: https://example.com)")
    parser.add_argument("--ui", choices=["textual", "tkinter", "cli"], default="textual", help="UI backend: textual, tkinter, or cli")
    parser.add_argument("--debug", action="store_true", help="Enable network timing and cache diagnostics")
    
    args = parser.parse_args()
    if args.debug:
        os.environ["NATO_BROWSER_DEBUG"] = "1"
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.url, ui_type=args.ui)


if __name__ == "__main__":
    main()
