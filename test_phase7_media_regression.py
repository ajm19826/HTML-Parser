"""Regression test for media metadata and form-control collection."""
from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom


def test_media_does_not_replace_control_metadata_collection():
    builder = DOMBuilder()
    builder.feed("<video controls><source src='clip.mp4'></video><form><button>Send</button></form>")
    rendered, _, controls = render_dom(builder.root)
    assert "Video format unsupported" in rendered
    assert any(kind == "button" for _, kind, _ in controls)
