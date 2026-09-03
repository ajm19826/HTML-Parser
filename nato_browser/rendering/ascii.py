"""Render a DOM tree into ASCII/terminal-friendly text with basic CSS/layout support."""
from __future__ import annotations

import textwrap
from typing import List, Tuple
from urllib.parse import urljoin

from nato_browser.html.dom import Element, Text
from nato_browser.css.parser import parse_inline, parse_stylesheet
from nato_browser.css.styles import compute_style
from nato_browser.css.selectors import compute_style_for_element, parse_rules
from nato_browser.rendering.images import fetch_image_bytes, image_bytes_to_ascii, get_ascii_for_url
from nato_browser.rendering import colors
from nato_browser.media.video import video_playback_available


def _render_text(node: Text, width: int) -> str:
    return textwrap.fill(node.data, width=width)


def _get_text(node) -> str:
    if isinstance(node, Text):
        return node.data
    if isinstance(node, Element):
        parts = []
        for c in node.children:
            parts.append(_get_text(c))
        return " ".join([p for p in parts if p])
    return ""


def _banner(text: str, width: int, level: int = 1) -> str:
    try:
        import pyfiglet

        font = "standard" if level <= 2 else "small"
        rendered = pyfiglet.figlet_format(text, font=font)
        lines = []
        for line in rendered.splitlines():
            lines.append(line[:width])
        # Color headings
        colored_lines = [colors.colorize(line, color="cyan", bold=True) for line in lines]
        return "\n" + "\n".join(colored_lines) + "\n"
    except Exception:
        text = text.upper() if level == 1 else text.capitalize()
        border = "=" * min(width, len(text) + 4)
        colored_text = colors.colorize(text, color="cyan", bold=True)
        colored_border = colors.colorize(border, color="cyan")
        return f"\n{colored_border}\n  {colored_text}\n{colored_border}\n"


def _apply_style(text: str, style: dict) -> str:
    """Apply ANSI styling based on CSS style dictionary."""
    if not style:
        return text
    
    kwargs = {}
    
    # Font weight
    if style.get("font-weight") in ("bold", "700", "800", "900"):
        kwargs["bold"] = True
    
    # Text decoration
    if style.get("text-decoration") == "underline":
        kwargs["underline"] = True
    
    # Color
    color = style.get("color")
    if color:
        kwargs["color"] = color
    
    return colors.colorize(text, **kwargs) if kwargs else text


def render_dom(root: Element, width: int = 80, base_url: str = "") -> Tuple[str, List[Tuple[int, str, str]], List[Tuple[int, str, dict]]]:
    out_lines: List[str] = []
    links: List[Tuple[int, str, str]] = []
    controls: List[Tuple[int, str, dict]] = []
    link_counter = 1

    # Gather style blocks anywhere in the document; selector matching happens per element.
    stylesheet_rules = []

    def collect_styles(node) -> None:
        if not isinstance(node, Element):
            return
        if node.tag == "style":
            css_text = " ".join(t.data for t in node.children if isinstance(t, Text))
            stylesheet_rules.extend(parse_rules(css_text))
        for child in node.children:
            collect_styles(child)

    collect_styles(root)

    def align_line(line: str, align: str, w: int) -> str:
        if align == "center":
            return line.center(w)
        if align == "right":
            return line.rjust(w)
        return line.ljust(w)

    def inline_text(node) -> str:
        nonlocal link_counter
        if isinstance(node, Text):
            return " ".join(node.data.split())
        if not isinstance(node, Element) or node.tag in ("script", "style"):
            return ""
        if node.tag == "br":
            return "\n"
        text = " ".join(part for part in (inline_text(child) for child in node.children) if part)
        if node.tag == "a":
            href = node.attrs.get("href", "") if node.attrs else ""
            link_text = text or href
            link_number = link_counter
            links.append((link_number, href, link_text))
            link_counter += 1
            return f"[{link_number}] {link_text}"
        return text

    form_counter = 0

    def walk(node, current_form: dict | None = None):
        nonlocal link_counter, out_lines, links, controls
        if isinstance(node, Text):
            out_lines.append(textwrap.fill(node.data, width=width))
            return
        if not isinstance(node, Element):
            return

        tag = node.tag
        
        # Skip script and style tags - don't render their content
        if tag in ("script", "style"):
            return
        style = compute_style(tag, {}, compute_style_for_element(node, stylesheet_rules))
        if style.get("display") == "none":
            return

        if style.get("display") == "flex":
            direction = style.get("flex-direction", "row").lower()
            gap = 1
            try:
                gap = max(0, int(str(style.get("gap", "1")).replace("px", "")))
            except ValueError:
                pass
            children = [child for child in node.children if isinstance(child, Element)]
            items = [inline_text(child).strip() or _get_text(child).strip() for child in children]
            items = [item for item in items if item]
            if direction == "column":
                for item in items:
                    out_lines.extend(textwrap.wrap(item, width=max(1, width)) or [""])
                out_lines.append("")
                return
            if not items:
                return
            rows: List[List[str]] = [[]]
            current_width = 0
            for item in items:
                item_width = min(width, max(1, len(item)))
                required = item_width + (gap if rows[-1] else 0)
                if style.get("flex-wrap", "nowrap").lower() == "wrap" and rows[-1] and current_width + required > width:
                    rows.append([])
                    current_width = 0
                    required = item_width
                rows[-1].append(item)
                current_width += required
            justify = style.get("justify-content", "flex-start").lower()
            for row in rows:
                content = (" " * gap).join(row)
                if justify in ("center", "flex-end", "end"):
                    content = content.center(width) if justify == "center" else content.rjust(width)
                elif justify in ("space-between", "space-around") and len(row) > 1:
                    available_gap = max(gap, (width - sum(len(item) for item in row)) // (len(row) - 1))
                    content = (" " * available_gap).join(row)
                out_lines.append(content[:width].ljust(width))
            out_lines.append("")
            return

        # headings
        if tag in ("h1", "h2"):
            text = _get_text(node) or tag
            rendered = _banner(text, width, level=1 if tag == "h1" else 2)
            out_lines.append(rendered)
            return
        if tag in ("h3", "h4", "h5", "h6"):
            text = _get_text(node) or tag
            colored_text = colors.colorize(text.upper(), color="cyan", bold=True)
            out_lines.append(colored_text)
            return

        if tag == "p":
            para = inline_text(node)
            lines = textwrap.wrap(para, width=width)
            align = style.get("text-align", "left")
            mt = int(style.get("margin-top", style.get("margin", "0")) or 0)
            mb = int(style.get("margin-bottom", style.get("margin", "0")) or 0)
            for _ in range(mt):
                out_lines.append("")
            for ln in lines:
                # Apply color if specified in style
                colored_ln = _apply_style(ln, style) if style else ln
                out_lines.append(align_line(colored_ln, align, width))
            for _ in range(mb):
                out_lines.append("")
            out_lines.append("")
            return

        if tag == "br":
            out_lines.append("")
            return
        if tag == "hr":
            hr_line = colors.colorize("─" * width, color="blue")
            out_lines.append(hr_line)
            return

        if tag in ("pre", "code"):
            code = "\n".join([c.data for c in node.children if isinstance(c, Text)])
            border_color = colors.colorize("┌" + "─" * (width - 2) + "┐", color="green")
            out_lines.append(border_color)
            for line in code.splitlines():
                # Color code content in magenta
                colored_line = colors.colorize(line.ljust(width - 2)[: width - 2], color="magenta")
                out_lines.append(colors.colorize("│", color="green") + colored_line + colors.colorize("│", color="green"))
            border_color_end = colors.colorize("└" + "─" * (width - 2) + "┘", color="green")
            out_lines.append(border_color_end)
            return

        if tag == "img":
            src = node.attrs.get("src", "") if node.attrs else ""
            alt = node.attrs.get("alt", "") if node.attrs else ""
            image_width = width
            if node.attrs:
                try:
                    image_width = min(width, max(1, int(node.attrs.get("width", width))))
                except (TypeError, ValueError):
                    pass
            image_url = urljoin(base_url, src) if base_url else src
            try:
                ascii_lines = get_ascii_for_url(image_url, width=min(60, image_width), use_color=True) if image_url else []
            except Exception:
                ascii_lines = []
            if ascii_lines:
                out_lines.extend(ascii_lines)
                return
            # Color image placeholder in yellow
            placeholder = colors.colorize(f"[image: {alt or src}]", color="yellow")
            out_lines.append(placeholder)
            return

        if tag in ("audio", "video"):
            # Render audio/video metadata
            src = node.attrs.get("src", "") if node.attrs else ""
            media_controls = "controls" in (node.attrs or {})
            media_type = "audio" if tag == "audio" else "video"
            
            # collect <source> children
            sources = []
            for child in node.children:
                if isinstance(child, Element) and child.tag == "source":
                    src_url = child.attrs.get("src", "") if child.attrs else ""
                    src_type = child.attrs.get("type", "") if child.attrs else ""
                    sources.append((src_url, src_type))
            
            # build display text
            if tag == "video" and not video_playback_available():
                out_lines.append(colors.colorize("[Video format unsupported]", color="yellow"))
                out_lines.append("")
                return
            if src or sources:
                out_lines.append(f"[{media_type.upper()}]")
                if src:
                    out_lines.append(f"  src: {src[:60]}")
                for src_url, src_type in sources:
                    type_str = f" ({src_type})" if src_type else ""
                    out_lines.append(f"  source: {src_url[:55]}{type_str}")
                if media_controls:
                    out_lines.append("  [playback controls]")
            else:
                out_lines.append(f"[{media_type.upper()}: no source]")
            out_lines.append("")
            return

        if tag == "a":
            href = node.attrs.get("href", "")
            link_text = _get_text(node) or href
            display = f"[{link_counter}] {link_text}"
            # Color links in bright blue with underline
            colored_display = colors.colorize(display, color="blue", underline=True, bold=True)
            out_lines.append(colored_display)
            links.append((link_counter, href, link_text))
            link_counter += 1
            return

        if tag == "input":
            # Render a simple input placeholder
            itype = node.attrs.get("type", "text") if node.attrs else "text"
            name = node.attrs.get("name", "") if node.attrs else ""
            value = node.attrs.get("value", "") if node.attrs else ""
            placeholder = node.attrs.get("placeholder", "") if node.attrs else ""
            display = f"[input:{itype} {name}='{value or placeholder}']"
            # Color inputs in yellow
            colored_display = colors.colorize(display, color="yellow")
            idx = len(out_lines)
            out_lines.append(colored_display)
            ctrl = {"type": itype, "name": name, "value": value, "placeholder": placeholder, "checked": "checked" in (node.attrs or {})}
            if current_form:
                ctrl["form"] = current_form.get("id")
                ctrl["form_action"] = current_form.get("action")
                ctrl["form_method"] = current_form.get("method")
            controls.append((idx, "input", ctrl))
            return

        if tag == "textarea":
            attrs = node.attrs or {}
            name = attrs.get("name", "")
            value = _get_text(node)
            idx = len(out_lines)
            out_lines.append(colors.colorize(f"[textarea: {name}]", color="yellow"))
            ctrl = {"type": "textarea", "name": name, "value": value, "placeholder": attrs.get("placeholder", "")}
            if current_form:
                ctrl.update({"form": current_form.get("id"), "form_action": current_form.get("action"), "form_method": current_form.get("method")})
            controls.append((idx, "textarea", ctrl))
            return

        if tag == "select":
            attrs = node.attrs or {}
            options = []
            selected = ""
            for child in node.children:
                if isinstance(child, Element) and child.tag == "option":
                    option_attrs = child.attrs or {}
                    option_value = option_attrs.get("value") or _get_text(child)
                    options.append((option_value, _get_text(child)))
                    if "selected" in option_attrs:
                        selected = option_value
            if not selected and options:
                selected = options[0][0]
            idx = len(out_lines)
            out_lines.append(colors.colorize(f"[select: {attrs.get('name', '')} = {selected}]", color="yellow"))
            ctrl = {"type": "select", "name": attrs.get("name", ""), "value": selected, "options": options}
            if current_form:
                ctrl.update({"form": current_form.get("id"), "form_action": current_form.get("action"), "form_method": current_form.get("method")})
            controls.append((idx, "select", ctrl))
            return

        if tag == "button":
            btn_text = _get_text(node) or (node.attrs.get("value") if node.attrs else "")
            idx = len(out_lines)
            # Color buttons in bright green
            colored_btn = colors.colorize(f"[button: {btn_text}]", color="green", bold=True)
            out_lines.append(colored_btn)
            ctrl = {"text": btn_text}
            if current_form:
                ctrl["form"] = current_form.get("id")
                ctrl["form_action"] = current_form.get("action")
                ctrl["form_method"] = current_form.get("method")
            controls.append((idx, "button", ctrl))
            return

        if tag == "ul":
            for li in node.children:
                if isinstance(li, Element) and li.tag == "li":
                    text = _get_text(li)
                    # Color list items with dimmed color
                    colored_item = colors.colorize("- " + textwrap.fill(text, width=width - 2), color="cyan")
                    out_lines.append(colored_item)
            out_lines.append("")
            return

        if tag == "ol":
            num = 1
            for li in node.children:
                if isinstance(li, Element) and li.tag == "li":
                    text = _get_text(li)
                    # Color ordered list items
                    colored_item = colors.colorize(f"{num}. " + textwrap.fill(text, width=width - 4), color="cyan")
                    out_lines.append(colored_item)
                    num += 1
            out_lines.append("")
            return
        
        if tag == "blockquote":
            # Render blockquotes with a special prefix
            quote_text = _get_text(node)
            lines = textwrap.wrap(quote_text, width=width - 4)
            # Color blockquote in gray
            colored_lines = [colors.colorize("  > " + line, color="gray") for line in lines]
            out_lines.extend(colored_lines)
            out_lines.append("")
            return

        if tag == "table":
            # Parse rows and cells with colspan/rowspan
            row_containers = [c for c in node.children if isinstance(c, Element) and c.tag in ("thead", "tbody", "tfoot")]
            trs = [c for c in node.children if isinstance(c, Element) and c.tag == "tr"]
            for container in row_containers:
                trs.extend(c for c in container.children if isinstance(c, Element) and c.tag == "tr")
            if not trs:
                return
            # Collect cells with spans
            table_cells = []  # list of list of cell dicts per row
            for tr in trs:
                row_cells = []
                for cell in tr.children:
                    if isinstance(cell, Element) and cell.tag in ("td", "th"):
                        text = _get_text(cell) or ""
                        colspan = 1
                        rowspan = 1
                        if cell.attrs:
                            try:
                                if cell.attrs.get("colspan"):
                                    colspan = max(1, int(cell.attrs.get("colspan")))
                                if cell.attrs.get("rowspan"):
                                    rowspan = max(1, int(cell.attrs.get("rowspan")))
                            except Exception:
                                pass
                        row_cells.append({"text": text, "colspan": colspan, "rowspan": rowspan, "is_header": cell.tag == "th"})
                table_cells.append(row_cells)

            # Build grid positions and origin mapping
            grid = []  # rows of origins or None
            origins = []  # list of origin dicts with position and spans
            for r_idx, row in enumerate(table_cells):
                # ensure grid has r_idx
                while len(grid) <= r_idx:
                    grid.append([])
                c_idx = 0
                for cell in row:
                    # find next free column
                    while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None:
                        c_idx += 1
                    # ensure row has enough columns
                    needed_cols = c_idx + cell["colspan"]
                    for rr in range(len(grid)):
                        if len(grid[rr]) < needed_cols:
                            grid[rr].extend([None] * (needed_cols - len(grid[rr])))
                    # mark occupied for rowspan/colspan
                    origin = {"r": r_idx, "c": c_idx, "text": cell["text"], "colspan": cell["colspan"], "rowspan": cell["rowspan"], "is_header": cell["is_header"]}
                    origins.append(origin)
                    for dr in range(cell["rowspan"]):
                        rr = r_idx + dr
                        while len(grid) <= rr:
                            grid.append([])
                        for dc in range(cell["colspan"]):
                            cc = c_idx + dc
                            while len(grid[rr]) <= cc:
                                grid[rr].append(None)
                            grid[rr][cc] = origin
                    c_idx += cell["colspan"]

            col_count = max(len(r) for r in grid) if grid else 0
            if col_count == 0:
                return
            
            # ===== Improved width solver with min-content and preferred-content =====
            def min_content_width(text: str) -> int:
                """Minimum width needed: longest word without wrapping."""
                words = text.split()
                return max((len(w) for w in words), default=0)
            
            def preferred_content_width(text: str, max_w: int = 60) -> int:
                """Optimal width for wrapped text (up to max_w)."""
                lines = textwrap.wrap(text, width=max_w) if text else [""]
                return max((len(line) for line in lines), default=0)
            
            # Step 1: Compute min-content for each column (from non-spanning cells)
            col_min = [1] * col_count
            for orig in origins:
                if orig["colspan"] == 1:
                    c = orig["c"]
                    txt = orig["text"].strip()
                    col_min[c] = max(col_min[c], min_content_width(txt))
            
            # Step 2: Compute preferred widths and distribute among columns
            col_preferred = col_min.copy()
            for orig in origins:
                span = orig["colspan"]
                if span > 1:
                    txt = orig["text"].strip()
                    # desired width for this cell across its span
                    desired = preferred_content_width(txt, max_w=80)
                    start, end = orig["c"], orig["c"] + span
                    current = sum(col_preferred[start:end]) + (span - 1) * 1
                    if desired > current:
                        # distribute excess to smallest columns in span
                        excess = desired - current
                        idxs = list(range(start, end))
                        idxs.sort(key=lambda i: col_preferred[i])
                        for i in range(excess):
                            col_preferred[idxs[i % len(idxs)]] += 1
            
            # Step 3: Fit to available width
            padding_and_borders = 3 * col_count + 1
            available = max(1, width - padding_and_borders)
            total_preferred = sum(col_preferred)
            
            if total_preferred > available:
                # Scale down but respect min-content
                total_min = sum(col_min)
                if total_min <= available:
                    # can fit with min widths, scale to available
                    ratio = (available - total_min) / max(1, total_preferred - total_min)
                    col_widths = [
                        col_min[i] + int((col_preferred[i] - col_min[i]) * ratio)
                        for i in range(col_count)
                    ]
                else:
                    # even min doesn't fit, scale all proportionally
                    ratio = available / total_min
                    col_widths = [max(1, int(col_min[i] * ratio)) for i in range(col_count)]
            else:
                # have extra space, grow proportionally
                col_widths = col_preferred.copy()
                extra = available - total_preferred
                i = 0
                while extra > 0:
                    col_widths[i % col_count] += 1
                    extra -= 1
                    i += 1
            
            # ===== Improved rowspan height balancing =====
            # Compute the minimum row heights required by rowspans
            row_min_height = [1] * len(grid)
            
            for orig in origins:
                rowspan = orig["rowspan"]
                if rowspan > 1:
                    # compute preferred height for this cell
                    span_w = sum(col_widths[orig["c"] : orig["c"] + orig["colspan"]]) + max(0, orig["colspan"] - 1) * 1
                    lines = textwrap.wrap(orig["text"], width=span_w) if orig["text"] else [""]
                    pref_height = max(1, len(lines))
                    # distribute across rows covered by rowspan
                    start_r, end_r = orig["r"], orig["r"] + rowspan
                    current_height = sum(row_min_height[start_r:end_r])
                    if pref_height > current_height:
                        # distribute excess to rows with smallest heights first
                        rows_in_span = list(range(start_r, end_r))
                        rows_in_span.sort(key=lambda rr: row_min_height[rr])
                        excess = pref_height - current_height
                        for i in range(excess):
                            row_min_height[rows_in_span[i % len(rows_in_span)]] += 1

            # draw top border
            sep = "┌" + "┬".join("─" * w for w in col_widths) + "┐"
            out_lines.append(sep)

            # render each row using pre-computed minimum heights
            for r in range(len(grid)):
                row_height = row_min_height[r] if r < len(row_min_height) else 1
                
                for line_idx in range(row_height):
                    row_line = "│"
                    c = 0
                    while c < col_count:
                        origin = grid[r][c] if c < len(grid[r]) else None
                        if origin is None:
                            # empty cell
                            cell_w = col_widths[c]
                            row_line += " " + "".ljust(cell_w) + " │"
                            c += 1
                            continue
                        # if this position is origin
                        if origin["r"] == r and origin["c"] == c:
                            span = origin["colspan"]
                            span_w = sum(col_widths[c : c + span]) + (span - 1) * 1
                            lines = textwrap.wrap(origin["text"], width=span_w) if origin["text"] else [""]
                            txt_line = lines[line_idx] if line_idx < len(lines) else ""
                            row_line += " " + txt_line.ljust(span_w) + " │"
                            c += span
                        else:
                            # covered by a span from earlier origin; skip printing cell and advance
                            c += 1
                    out_lines.append(row_line)

            out_lines.append("└" + "┴".join("─" * w for w in col_widths) + "┘")
            return

        # Form container: collect form attrs and pass through context
        if tag == "form":
            form_counter_local = len([c for c in controls if c and True]) + 1
            form_attrs = node.attrs or {}
            form_method = str(form_attrs.get("method") or "get").upper()
            form_meta = {
                "id": form_counter_local,
                "action": form_attrs.get("action") or "",
                "method": form_method,
            }
            for child in node.children:
                walk(child, current_form=form_meta)
            return

        # Generic: walk children
        for child in node.children:
            walk(child, current_form=current_form)

    # start from body if present
    body = None
    for c in root.children:
        if isinstance(c, Element) and c.tag == "body":
            body = c
            break
    if body is None:
        body = root

    for child in body.children:
        walk(child)

    return "\n".join(out_lines), links, controls
