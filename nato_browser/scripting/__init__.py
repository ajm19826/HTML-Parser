"""Optional, sandboxed JavaScript execution boundary."""
from nato_browser.scripting.engine import JavaScriptEngine, NullJavaScriptEngine, create_javascript_engine

__all__ = ["JavaScriptEngine", "NullJavaScriptEngine", "create_javascript_engine"]
