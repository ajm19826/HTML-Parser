"""Tkinter-based GUI for the NATO ASCII Browser."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import List, Tuple, Dict, Any
from urllib.parse import urljoin
import threading

from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom
from nato_browser.network.http import fetch, DEFAULT_TIMEOUT


class NatoTkinterApp:
    """Tkinter GUI for the NATO ASCII Browser."""

    def __init__(self, initial_url: str = "https://example.com", width: int = 900, height: int = 700):
        self.root = tk.Tk()
        self.root.title("NATO ASCII Browser")
        self.root.geometry(f"{width}x{height}")

        self.url = initial_url
        self.history: List[str] = []
        self.index = -1
        self.skip_quit_confirmation = False
        self.render_width = 100  # default rendering width in chars

        # Control registry: maps widget id to metadata
        self._control_registry: Dict[int, Tuple[str, dict]] = {}

        # Link registry: maps link number to URL
        self._link_registry: Dict[int, str] = {}

        # Setup UI
        self._create_ui()
        self.root.bind("<Alt-q>", lambda _event: self._quit())
        self.root.bind("<Control-c>", lambda _event: self._confirm_quit())

        # Load initial URL
        self.root.after(100, lambda: self._load_url_async(initial_url))

    def _create_ui(self):
        """Create the Tkinter UI layout."""
        # Top frame: URL bar and buttons
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(top_frame, width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.insert(0, self.url)
        self.url_entry.bind("<Return>", lambda e: self._on_url_submitted())

        ttk.Button(top_frame, text="Load", command=self._on_url_submitted).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="← Back", command=self._back).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Forward →", command=self._forward).pack(side=tk.LEFT, padx=2)

        # Status bar
        self.status_var = tk.StringVar(value="Loading...")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(
            fill=tk.X, side=tk.BOTTOM, padx=2, pady=2
        )

        # Content frame with scrolled text widget
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Use a Canvas with a Frame inside to support embedded widgets
        self.canvas = tk.Canvas(content_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=10)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mouse wheel for scrolling
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))  # Linux scroll up
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))   # Linux scroll down

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_url_submitted(self):
        """Handle URL entry submission."""
        url = self.url_entry.get().strip()
        if url:
            self._load_url_async(url)

    def _load_url_async(self, url: str, push_history: bool = True, force_refresh: bool = False):
        """Load URL in a background thread to avoid blocking UI."""
        self.status_var.set(f"Loading {url}...")

        def load():
            try:
                final_url, html, headers, status = fetch(url, timeout=DEFAULT_TIMEOUT, force_refresh=force_refresh)
                if status == 0:
                    self.root.after(0, lambda: self._on_load_error(f"Failed to load {url}"))
                    return
                builder = DOMBuilder()
                builder.feed(html)
                rendered, links, controls = render_dom(builder.root, width=self.render_width, base_url=final_url)
                self.root.after(0, lambda: self._on_page_ready(final_url, rendered, links, controls, status, push_history))
            except Exception as e:
                self.root.after(0, lambda: self._on_load_error(str(e)))

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def _on_page_ready(self, final_url: str, rendered: str, links: List[Tuple[int, str, str]], controls: List[Tuple[int, str, dict]], status: int, push_history: bool = True):
        """Apply already-rendered page data on Tk's UI thread."""
        self.url = final_url
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, final_url)
        self._set_content(rendered, links, controls)

        # Update history
        if push_history:
            if self.index < len(self.history) - 1:
                self.history = self.history[: self.index + 1]
            self.history.append(final_url)
            self.index = len(self.history) - 1

        self.status_var.set(f"Loaded {final_url} ({status}) - {len(links)} links")

    def _on_load_error(self, error: str):
        """Handle load error."""
        self.status_var.set(f"Error: {error}")
        messagebox.showerror("Error", error)

    def _set_content(self, rendered_text: str, links: List[Tuple[int, str, str]], controls: List[Tuple[int, str, dict]]):
        """Set the content in the scrollable frame."""
        # Clear previous widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self._control_registry.clear()
        self._link_registry = {num: url for num, url, text in links}

        # Create text widget to display rendered content
        text_widget = tk.Text(
            self.scrollable_frame,
            wrap=tk.NONE,
            bg="white",
            fg="black",
            font=("Courier New", 9),
            height=30,
            width=self.render_width,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Configure tags
        text_widget.tag_config("link", foreground="blue", underline=True)
        text_widget.tag_config("control", foreground="green")
        text_widget.tag_config("header", foreground="darkred", font=("Courier New", 9, "bold"))

        # Insert text and apply tags
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, rendered_text)

        # Apply link tags
        for link_num, url, link_text in links:
            # Find "[N]" pattern in text and tag it
            search_str = f"[{link_num}]"
            pos = "1.0"
            while True:
                pos = text_widget.search(search_str, pos, nocase=False)
                if not pos:
                    break
                end_pos = f"{pos}+{len(search_str)}c"
                text_widget.tag_add("link", pos, end_pos)
                # Bind click event
                text_widget.tag_bind("link", "<Button-1>", lambda e, u=url: self._on_link_click(u))
                pos = end_pos

        text_widget.config(state=tk.DISABLED)

        # Insert control widgets (inputs, buttons) below the text
        self._insert_controls(controls)

    def _insert_controls(self, controls: List[Tuple[int, str, dict]]):
        """Insert interactive control widgets (inputs, buttons) into the frame."""
        for idx, ctrl_type, ctrl_meta in controls:
            if ctrl_type == "input":
                # Create an input field
                frame = ttk.Frame(self.scrollable_frame)
                frame.pack(fill=tk.X, pady=5)

                name = ctrl_meta.get("name", "")
                placeholder = ctrl_meta.get("placeholder", "")
                itype = ctrl_meta.get("type", "text")
                value = ctrl_meta.get("value", "")

                label_text = f"{name}:" if name else f"[{itype}]"
                ttk.Label(frame, text=label_text, width=15).pack(side=tk.LEFT, padx=5)

                if itype in ("checkbox", "radio"):
                    variable = tk.BooleanVar(value=bool(ctrl_meta.get("checked")))
                    entry = ttk.Checkbutton(frame, text=label_text, variable=variable)
                    entry.pack(side=tk.LEFT, padx=5)
                    ctrl_meta = {**ctrl_meta, "variable": variable}
                elif itype == "range":
                    entry = ttk.Scale(frame, from_=0, to=100, orient=tk.HORIZONTAL)
                    entry.set(float(value or 0))
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                elif itype == "number":
                    entry = ttk.Spinbox(frame, from_=-1000000, to=1000000, width=40)
                    entry.insert(0, value or placeholder)
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                else:
                    entry = ttk.Entry(frame, width=40, show="*" if itype == "password" else "")
                    entry.insert(0, value or placeholder)
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

                widget_id = id(entry)
                self._control_registry[widget_id] = (ctrl_type, {**ctrl_meta, "widget": entry})

            elif ctrl_type == "textarea":
                frame = ttk.Frame(self.scrollable_frame)
                frame.pack(fill=tk.X, pady=5)
                name = ctrl_meta.get("name", "")
                ttk.Label(frame, text=f"{name}:", width=15).pack(side=tk.LEFT, padx=5)
                entry = tk.Text(frame, height=4, width=40)
                entry.insert("1.0", ctrl_meta.get("value", ""))
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                self._control_registry[id(entry)] = (ctrl_type, {**ctrl_meta, "widget": entry})

            elif ctrl_type == "select":
                frame = ttk.Frame(self.scrollable_frame)
                frame.pack(fill=tk.X, pady=5)
                name = ctrl_meta.get("name", "")
                ttk.Label(frame, text=f"{name}:", width=15).pack(side=tk.LEFT, padx=5)
                values = [label for _, label in ctrl_meta.get("options", [])]
                entry = ttk.Combobox(frame, values=values, state="readonly", width=38)
                selected = ctrl_meta.get("value", "")
                if selected in values:
                    entry.set(selected)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                self._control_registry[id(entry)] = (ctrl_type, {**ctrl_meta, "widget": entry})

            elif ctrl_type == "button":
                frame = ttk.Frame(self.scrollable_frame)
                frame.pack(fill=tk.X, pady=5)

                btn_text = ctrl_meta.get("text", "Submit")
                form_action = ctrl_meta.get("form_action", self.url)
                form_method = ctrl_meta.get("form_method", "GET")

                def on_button_click(action=form_action, method=form_method):
                    self._on_form_submit(action, method)

                btn = ttk.Button(frame, text=btn_text, command=on_button_click)
                btn.pack(side=tk.LEFT, padx=5)

                widget_id = id(btn)
                self._control_registry[widget_id] = (ctrl_type, {**ctrl_meta})

    def _on_link_click(self, url: str):
        """Handle link click."""
        # Resolve relative URLs
        resolved_url = urljoin(self.url, url)
        self._load_url_async(resolved_url)

    def _on_form_submit(self, action: str, method: str):
        """Handle form submission."""
        # Gather input values
        payload = {}
        for widget_id, (ctrl_type, ctrl_meta) in self._control_registry.items():
            if ctrl_type == "input":
                widget = ctrl_meta.get("widget")
                name = ctrl_meta.get("name", "")
                if widget and name:
                    if ctrl_meta.get("type") in ("checkbox", "radio"):
                        payload[name] = "on" if ctrl_meta["variable"].get() else ""
                    else:
                        payload[name] = widget.get()
            elif ctrl_type == "textarea":
                widget = ctrl_meta.get("widget")
                if widget and ctrl_meta.get("name"):
                    payload[ctrl_meta["name"]] = widget.get("1.0", tk.END).rstrip("\n")
            elif ctrl_type == "select":
                widget = ctrl_meta.get("widget")
                if widget and ctrl_meta.get("name"):
                    payload[ctrl_meta["name"]] = widget.get()

        # Resolve target URL
        target = urljoin(self.url, action or self.url)

        if method.upper() == "GET":
            # Build query string
            if payload:
                from urllib.parse import urlencode

                query_string = urlencode(payload)
                target = f"{target}?{query_string}"
            self._load_url_async(target)
        else:
            # POST submission
            self.status_var.set(f"Submitting form to {action} ({method})...")
            self.root.update()

            def post():
                try:
                    final_url, html, headers, status = fetch(target, timeout=DEFAULT_TIMEOUT, method=method, data=payload)
                    builder = DOMBuilder()
                    builder.feed(html)
                    rendered, links, controls = render_dom(builder.root, width=self.render_width, base_url=final_url)
                    self.root.after(0, lambda: self._on_page_ready(final_url, rendered, links, controls, status))
                except Exception as e:
                    self.root.after(0, lambda: self._on_load_error(str(e)))

            thread = threading.Thread(target=post, daemon=True)
            thread.start()

    def _back(self):
        """Navigate back in history."""
        if self.index > 0:
            self.index -= 1
            url = self.history[self.index]
            self._load_url_async(url, push_history=False)

    def _forward(self):
        """Navigate forward in history."""
        if self.index < len(self.history) - 1:
            self.index += 1
            url = self.history[self.index]
            self._load_url_async(url, push_history=False)

    def _quit(self):
        self.root.destroy()

    def _confirm_quit(self):
        if self.skip_quit_confirmation:
            self._quit()
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Quit NATO ASCII Browser?")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Do you want to quit?").pack(padx=20, pady=(16, 8))
        never_ask = tk.BooleanVar(value=False)
        ttk.Checkbutton(dialog, text="Never ask me again", variable=never_ask).pack(padx=20, pady=4)
        buttons = ttk.Frame(dialog)
        buttons.pack(pady=(8, 16))

        def finish(quit_app: bool):
            if never_ask.get():
                self.skip_quit_confirmation = True
            dialog.destroy()
            if quit_app:
                self._quit()

        ttk.Button(buttons, text="Quit", command=lambda: finish(True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Cancel", command=lambda: finish(False)).pack(side=tk.LEFT, padx=5)
        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))

    def run(self):
        """Start the Tkinter event loop."""
        self.root.mainloop()


def main(url: str = "https://example.com"):
    """Entry point for Tkinter browser."""
    app = NatoTkinterApp(initial_url=url)
    app.run()


if __name__ == "__main__":
    import sys

    initial_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    main(initial_url)
