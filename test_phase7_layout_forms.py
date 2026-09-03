"""Phase 7 layout and form regression tests."""
from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom


def test_flex_row_with_gap_and_wrap():
    builder = DOMBuilder()
    builder.feed("<style>.row { display:flex; gap:4; flex-wrap:wrap }</style><div class='row'><span>A</span><span>B</span><span>C</span></div>")
    rendered, _, _ = render_dom(builder.root, width=20)
    assert "A    B    C" in rendered


def test_form_control_metadata():
    builder = DOMBuilder()
    builder.feed("""<form action='/submit'>
        <textarea name='message'>hello</textarea>
        <select name='country'><option value='us'>United States</option><option value='ca'>Canada</option></select>
        <input type='checkbox' name='remember' checked>
        <input type='radio' name='plan' value='basic'>
        <input type='range' name='volume' value='50'>
        <input type='number' name='age' value='21'>
        <input type='date' name='day'>
        <button>Send</button>
    </form>""")
    rendered, _, controls = render_dom(builder.root)
    kinds = [kind for _, kind, _ in controls]
    assert "textarea" in kinds
    assert "select" in kinds
    assert kinds.count("input") == 5
    assert "button" in kinds
    checkbox = next(meta for _, kind, meta in controls if kind == "input" and meta["type"] == "checkbox")
    assert checkbox["checked"] is True


def test_missing_form_method_defaults_to_get():
    builder = DOMBuilder()
    builder.feed("<form><input name='q'></form>")
    _, _, controls = render_dom(builder.root)
    assert controls[0][2]["form_method"] == "GET"
