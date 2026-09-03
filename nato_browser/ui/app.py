"""Textual-based UI for NATO ASCII Browser (Phase 2)."""
from __future__ import annotations

import asyncio
import re
from typing import List, Tuple

from textual.app import App
from textual.widgets import Input, Header, Static, Button, Checkbox, Select, TextArea
from textual.containers import VerticalScroll
from textual.events import MouseDown
from textual.reactive import reactive
from textual.screen import ModalScreen
from urllib.parse import urljoin

from nato_browser.network.http import DEFAULT_TIMEOUT, fetch
from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom
from nato_browser.debugging import debug_session, format_dom_tree


Link = Tuple[int, str, str]


class Viewport(VerticalScroll):
    links: List[Link] = []
    async def set_content(self, text: str, links: List[Link], controls: List[Tuple[int, str, dict]] | None = None):
        """Mount content by splitting into lines and replacing placeholders
        like `[input:...]` and `[button: ...]` with interactive widgets.
        """
        self.links = links
        lines = text.splitlines()
        control_map = {c[0]: (c[1], c[2]) for c in (controls or [])}
        await self.remove_children()
        # create a vertical column of widgets for each line
        for i, ln in enumerate(lines):
            ln_stripped = ln.strip()
            # input placeholder format: [input:type name='value']
            # if we have structured control metadata, use it
            if i in control_map:
                ctype, attrs = control_map[i]
                if ctype == "input":
                    val = attrs.get("value") or attrs.get("placeholder") or ""
                    itype = attrs.get("type", "text")
                    widget_name = f"ctrl_input_{i}"
                    if itype in ("checkbox", "radio"):
                        inp = Checkbox(attrs.get("name", ""), value=bool(attrs.get("checked")), name=attrs.get("name", ""), id=widget_name)
                    else:
                        inp = Input(value=val, placeholder=f"{itype}", name=attrs.get("name", ""), id=widget_name)
                    await self.mount(inp)
                    # register control metadata with app
                    meta = {"type": "input", "name": attrs.get("name", ""), "form": attrs.get("form"), "form_action": attrs.get("form_action"), "form_method": attrs.get("form_method")}
                    if hasattr(self.app, "_register_control"):
                        meta["widget"] = inp
                        self.app._register_control(widget_name, meta)
                    continue
                    if ctype == "textarea":
                        widget_name = f"ctrl_textarea_{i}"
                        area = TextArea(attrs.get("value", ""), name=attrs.get("name", ""), id=widget_name)
                        await self.mount(area)
                        attrs["widget"] = area
                        self.app._register_control(widget_name, {**attrs, "type": "textarea"})
                        continue
                    if ctype == "select":
                        widget_name = f"ctrl_select_{i}"
                        options = [(label, value) for value, label in attrs.get("options", [])]
                        select = Select(options, value=attrs.get("value") or Select.NULL, name=attrs.get("name", ""), id=widget_name)
                        await self.mount(select)
                        attrs["widget"] = select
                        self.app._register_control(widget_name, {**attrs, "type": "select"})
                        continue
                if ctype == "button":
                    widget_name = f"ctrl_btn_{i}"
                    btn = Button(label=attrs.get("text", ""), name=widget_name)
                    await self.mount(btn)
                    meta = {"type": "button", "form": attrs.get("form"), "form_action": attrs.get("form_action"), "form_method": attrs.get("form_method")}
                    if hasattr(self.app, "_register_control"):
                        self.app._register_control(widget_name, meta)
                    continue
            # default: static line (possibly containing link numbers)
            await self.mount(LinkStatic(ln, links))


class QuitScreen(ModalScreen[tuple[bool, bool]]):
    def compose(self):
        yield Static("Do you want to quit?", id="quit-message")
        yield Checkbox("Never ask me again", id="never-ask")
        yield Button("Quit", id="quit-confirm")
        yield Button("Cancel", id="quit-cancel")

    async def on_button_pressed(self, event) -> None:
        should_quit = event.button.id == "quit-confirm"
        never_ask = self.query_one("#never-ask", Checkbox).value
        self.dismiss((should_quit, never_ask))


class DebugScreen(ModalScreen[None]):
    def __init__(self, app: "NatoApp", **kwargs):
        super().__init__(**kwargs)
        self.browser_app = app

    def compose(self):
        snapshot = debug_session.snapshot()
        network = "\n".join(
            f"{item['method']} {item['url']} {item['status']} {item['bytes']} bytes {item['elapsed_ms']} ms"
            for item in snapshot["network"][-20:]
        ) or "No requests"
        media = "\n".join(str(item) for item in snapshot["media"][-20:]) or "No media"
        css = "\n".join(snapshot["css"]) or "No stylesheet details"
        console = "\n".join(snapshot["console"][-20:]) or "No console messages"
        panel = (
            "DOM\n" + (self.browser_app.debug_dom or "No document") +
            "\n\nCSS\n" + css +
            "\n\nNETWORK\n" + network +
            "\n\nMEDIA\n" + media +
            "\n\nCONSOLE\n" + console
        )
        yield Static(panel, id="debug-panel")
        yield Button("Close", id="debug-close")

    async def on_button_pressed(self, event) -> None:
        self.dismiss()


class NatoApp(App):
    CSS_PATH = None
    BINDINGS = [
        ("ctrl+l", "focus_url", "Focus URL"),
        ("ctrl+r", "reload", "Reload"),
        ("alt+left", "back", "Back"),
        ("alt+right", "forward", "Forward"),
        ("alt+q", "quit", "Quit"),
        ("ctrl+c", "confirm_quit", "Quit"),
        ("f12", "debug", "Developer Tools"),
    ]

    url = reactive("")

    def __init__(self, initial_url: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.initial_url = initial_url
        self.history: List[str] = []
        self.index = -1
        self._control_registry: dict[str, dict] = {}
        self.skip_quit_confirmation = False
        self.debug_dom = ""

    def compose(self):
        yield Header()
        self.input = Input(placeholder="Enter URL and press Enter", name="urlbar")
        yield self.input
        self.viewport = Viewport()
        yield self.viewport
        self.status = Static("Ready", id="status")
        yield self.status

    async def on_mount(self) -> None:
        self.input.on_submit = self.on_url_submitted  # type: ignore

        if self.initial_url:
            await self.load_url(self.initial_url)

    def _register_control(self, name: str, meta: dict):
        self._control_registry[name] = meta

    def _get_control_meta(self, name: str) -> dict | None:
        return self._control_registry.get(name)

    async def on_url_submitted(self, value: str) -> None:  # called by Input
        await self.load_url(value)

    async def submit_form(self, action: str, method: str, payload: dict):
        """Submit a form and load the response into the TUI (supports GET/POST)."""
        import asyncio

        self.set_footer_text(f"Submitting form to {action} ({method})")
        # run fetch in thread
        final, html, headers, status = await asyncio.to_thread(fetch, action, DEFAULT_TIMEOUT, method, payload)
        builder = DOMBuilder()
        try:
            builder.feed(html)
        except Exception:
            # if response is not HTML, show raw text
            rendered = html[: self.size.width * 10]
            await self.viewport.set_content(rendered, [], [])
            self.set_footer_text(f"Submitted to {final} status={status}")
            return

        dom = builder.root
        self.debug_dom = format_dom_tree(dom)
        rendered, links, controls = render_dom(dom, width=self.size.width - 4, base_url=final)
        # clear registry and set content
        self._control_registry = {}
        await self.viewport.set_content(rendered, links, controls)
        # push to history
        if self.index < len(self.history) - 1:
            self.history = self.history[: self.index + 1]
        self.history.append(final)
        self.index = len(self.history) - 1
        self.set_footer_text(f"Loaded {final} status={status} links={len(links)}")

    async def load_url(self, url: str, push_history: bool = True, force_refresh: bool = False):
        url = self._normalize(url)
        self.url = url
        self.set_footer_text(f"Loading: {url}")
        # network and parsing in background thread
        final, html, headers, status = await asyncio.to_thread(fetch, url, force_refresh=force_refresh)
        builder = DOMBuilder()
        builder.feed(html)
        dom = builder.root
        self.debug_dom = format_dom_tree(dom)
        rendered, links, controls = render_dom(dom, width=self.size.width - 4, base_url=final)

        # clear registry for new page
        self._control_registry = {}
        await self.viewport.set_content(rendered, links, controls)
        self.set_footer_text(f"Loaded {final}  status={status}  links={len(links)}")

        if push_history:
            if self.index < len(self.history) - 1:
                self.history = self.history[: self.index + 1]
            self.history.append(final)
            self.index = len(self.history) - 1

    def _normalize(self, url: str) -> str:
        url = url.strip()
        if not url:
            return url
        if not re.match(r"^https?://", url):
            url = "https://" + url
        return url

    def set_footer_text(self, text: str):
        self.status.update(text)

    async def action_focus_url(self) -> None:
        await self.set_focus(self.input)

    async def action_reload(self) -> None:
        if self.index >= 0:
            await self.load_url(self.history[self.index], push_history=False, force_refresh=True)

    async def action_back(self) -> None:
        if self.index > 0:
            self.index -= 1
            await self.load_url(self.history[self.index], push_history=False)

    async def action_forward(self) -> None:
        if self.index < len(self.history) - 1:
            self.index += 1
            await self.load_url(self.history[self.index], push_history=False)

    async def action_quit(self) -> None:
        self.exit()

    async def action_debug(self) -> None:
        await self.push_screen(DebugScreen(self))

    async def action_confirm_quit(self) -> None:
        if self.skip_quit_confirmation:
            await self.action_quit()
            return

        def handle_result(result: tuple[bool, bool] | None) -> None:
            if result:
                should_quit, never_ask = result
                if never_ask:
                    self.skip_quit_confirmation = True
            else:
                should_quit = False
            if should_quit:
                self.exit()

        await self.push_screen(QuitScreen(), handle_result)

    async def on_button_pressed(self, event) -> None:  # type: ignore
        # Collect input values in the viewport and show summary in footer
        try:
            # identify which button was pressed
            sender = getattr(event, "button", None) or getattr(event, "sender", None)
            name = getattr(sender, "name", None)
            meta = self._get_control_meta(name) if name else None
            # collect inputs
            if meta and meta.get("form"):
                # submit the form
                form_id = meta.get("form")
                # find form controls matching this form id from registry
                # registry entries store 'form' property where applicable
                form_inputs = {k: v for k, v in self._control_registry.items() if v.get("form") == form_id}
                # assemble payload from mounted inputs by name
                payload = {}
                for control_name, control in self._control_registry.items():
                    if control.get("form") != form_id or not control.get("name"):
                        continue
                    widget = control.get("widget")
                    if isinstance(widget, Checkbox):
                        payload[control["name"]] = "on" if widget.value else ""
                    elif isinstance(widget, Select):
                        payload[control["name"]] = "" if widget.value is Select.NULL else str(widget.value)
                    elif isinstance(widget, TextArea):
                        payload[control["name"]] = widget.text
                    elif widget is not None:
                        payload[control["name"]] = widget.value
                # perform submit according to method
                action = None
                for v in form_inputs.values():
                    if v.get("form_action"):
                        action = v.get("form_action")
                        break
                action = urljoin(self.url, action or self.url)
                method = None
                for v in form_inputs.values():
                    if v.get("form_method"):
                        method = v.get("form_method")
                        break
                method = method or "GET"
                if method.upper() == "GET":
                    # build query string
                    from urllib.parse import urlencode, urljoin

                    query = urlencode(payload)
                    target = action
                    if not target:
                        target = self.url
                    if "?" in target:
                        target = target + "&" + query
                    else:
                        target = target + ("?" + query if query else "")
                    await self.load_url(target)
                else:
                    # POST via fetch in background
                    # perform submit and load response into the app
                    await self.submit_form(action or self.url, method.upper(), payload)
                return
            self.set_footer_text("No form submitter selected")
        except Exception:
            self.set_footer_text("Button pressed")

    async def on_key(self, event) -> None:  # naive numeric link handling
        key = getattr(event, "key", None)
        if not key:
            return
        # Enter in URL input -> navigate
        if key == "enter":
            try:
                if hasattr(self, "input") and self.input.has_focus:
                    await self.load_url(self.input.value)
                    return
            except Exception:
                pass

        if key.isdigit():
            idx = int(key)
            match = [l for l in self.viewport.links if l[0] == idx]
            if match:
                _, href, _ = match[0]
                await self.load_url(urljoin(self.url, href))


class LinkStatic(Static):
    """Static widget that understands numbered link lines like '[1] Text' and handles clicks."""

    def __init__(self, text: str, links: List[Link], **kwargs):
        super().__init__(text, **kwargs)
        self.links = {str(i): href for i, href, _ in links}
        self.lines = text.splitlines()

    async def on_mouse_down(self, event: MouseDown) -> None:  # type: ignore[override]
        # compute clicked line index relative to widget
        rel_y = event.y
        if rel_y < 0 or rel_y >= len(self.lines):
            return
        line = self.lines[rel_y]
        # look for leading [n]
        import re

        m = re.match(r"\s*\[(\d+)\]", line)
        if m:
            idx = m.group(1)
            href = self.links.get(idx)
            if href:
                # ask parent app to load
                app = self.app
                if hasattr(app, "load_url"):
                    await app.load_url(urljoin(app.url, href))
