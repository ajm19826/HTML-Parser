"""Deterministic Phase 7 tests for selectors and resource rendering."""
from unittest.mock import patch

from nato_browser.css.selectors import compute_style_for_element, matches, parse_rules
from nato_browser.html.dom import Element
from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom


def test_selector_matching():
    root = Element("html")
    body = Element("body")
    main = Element("main", {"id": "main", "class": "content warning"})
    paragraph = Element("p", {"class": "warning"})
    anchor = Element("a", {"href": "/docs"})
    root.append(body)
    body.append(main)
    main.append(paragraph)
    paragraph.append(anchor)

    assert matches(paragraph, "p.warning")
    assert matches(paragraph, ".warning")
    assert matches(paragraph, "main p")
    assert matches(anchor, "p > a")
    assert not matches(anchor, "main > a")


def test_selector_specificity_and_important():
    element = Element("p", {"id": "intro", "class": "warning", "style": "color: green"})
    rules = parse_rules("p { color: white } .warning { color: red } #intro { color: blue }")
    assert compute_style_for_element(element, rules)["color"] == "green"
    important_rules = parse_rules("#intro { color: blue !important }")
    assert compute_style_for_element(element, important_rules)["color"] == "blue"


def test_descendant_and_child_render_styles():
    html = """<style>nav a { color: red; text-decoration: underline } .warning { color: #00ff00 }</style>
    <nav><a href='/docs'>Docs</a></nav><p class='warning'>Alert</p>"""
    builder = DOMBuilder()
    builder.feed(html)
    rendered, links, _ = render_dom(builder.root, base_url="https://example.test/page")
    assert links == [(1, "/docs", "Docs")]
    assert "\x1b[" in rendered
    assert "Docs" in rendered and "Alert" in rendered


def test_tbody_table_renders():
    builder = DOMBuilder()
    builder.feed("<table><tbody><tr><td>Cell</td></tr></tbody></table>")
    rendered, _, _ = render_dom(builder.root)
    assert "Cell" in rendered


def test_relative_image_is_converted_inside_page():
    with patch("nato_browser.rendering.ascii.get_ascii_for_url", return_value=["  /\\"] ) as converter:
        builder = DOMBuilder()
        builder.feed("<img src='media/cat.png' width='20' alt='Cat'>")
        rendered, _, _ = render_dom(builder.root, width=80, base_url="https://example.test/articles/page")
    converter.assert_called_once_with("https://example.test/articles/media/cat.png", width=20, use_color=True)
    assert "/\\" in rendered
