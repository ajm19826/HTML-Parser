# NATO ASCII Browser

Incremental ASCII browser implementation in Python with Textual TUI and Tkinter GUI support. Phases 1–7 complete for the supported terminal feature set, with explicit capability boundaries for optional media playback and JavaScript.

**Latest Updates (Phases 4–5 + Tkinter UI + Robustness/Colors):**
- Phase 4.1: Interactive form rendering (input fields, buttons; GET/POST submission)
- Phase 4.2: Improved table solver with min-content/preferred-content widths + rowspan height balancing
- Phase 4.3: Image ASCII conversion (grayscale + optional ANSI 256-color dithering)
- Phase 4.4: Form POST response loading into TUI
- Phase 4.5: Image disk caching + enhanced character ramp
- Phase 5: Audio/video metadata rendering (displays `<audio>`, `<video>`, and `<source>` tags with URLs)
- **Tkinter GUI:** Full-featured web browser GUI with scrolling, clickable links, and interactive forms
- **Robustness:** Enhanced HTML parser with error recovery, expanded void tags, better handling of malformed markup
- **Colors:** Comprehensive ANSI 256-color support with CSS color mapping, color schemes for different element types
- **Phase 6:** Bounded GET page cache with TTL, cache controls, and opt-in network timing diagnostics
- **Phase 7:** CSS selector matching, flex layout, practical form controls, real image embedding, developer diagnostics, and optional PyAV video decoding

## Install

```bash
pip install -r requirements.txt
```

For CLI command support, install in development mode:
```bash
pip install -e .
```

## Run

**Textual TUI (Terminal UI):**
```bash
python -m nato_browser https://example.com
# or
nato-browser-tui https://example.com
```

**Tkinter GUI (Graphical UI):**
```bash
python -m nato_browser --ui tkinter https://example.com
# or
nato-browser-gui https://example.com
```

**Default (Textual TUI):**
```bash
nato-browser https://example.com
```

**Explicit CLI mode:**
```bash
python -m nato_browser https://example.com --ui cli
```

All network requests are capped at a ten-second overall deadline, including fallback handling. Failed or timed-out requests are reported without attempting to render an empty page.

**Smoke Tests:**
```bash
python run_tests.py
python -m pytest test_phase6.py
```

**Debug Diagnostics:**
```bash
python -m nato_browser https://example.com --debug
```

The page cache stores successful, non-authenticated GET responses for five minutes, with a maximum of 64 entries. Use `--debug` or set `NATO_BROWSER_DEBUG=1` to log request timing, status, response size, and cache behavior.

**Optional video decoding:**
```bash
pip install -e ".[video]"
```

PyAV provides asynchronous frame decoding and bounded buffering through `nato_browser.media.video.VideoPlayer`. Without PyAV, video is reported as `[Video format unsupported]`; DRM is never bypassed. Audio routing still requires platform audio-output integration.

## Features

### Core
- URL fetching (requests or urllib fallback)
- HTML → DOM parsing (robust handling of malformed HTML, auto-closing tags)
- CSS inline + stylesheet parsing, computed styles
- ASCII/terminal-friendly rendering with ANSI color support

### Robustness & Compatibility
- **HTML5 Support:** Extended void tag list (area, base, embed, keygen, param, track, wbr)
- **Error Recovery:** Graceful handling of unbalanced tags, malformed markup, encoding issues
- **CSS Parsing:** Comments removal, comma-separated selectors, class/ID selectors with tag extraction
- **CSS Selectors:** Element, class, ID, descendant, child, comma-separated selectors, specificity, and `!important`
- **Malformed HTML:** Auto-recovery from missing closing tags, improper nesting

### Color Support
- **ANSI 256-color palette** with CSS color name mapping (red, blue, green, etc.)
- **Hex color support** (#FF0000 format)
- **RGB color support** (rgb(255, 0, 0) format)
- **Color Schemes:**
  - Headings: cyan with bold
  - Links: bright blue with underline and bold
  - Code blocks: magenta text with green borders
  - Input fields: yellow
  - Buttons: bright green with bold
  - List items: cyan
  - Blockquotes: gray with `> ` prefix
  - Images: yellow placeholders
  - Horizontal rules: blue

### Rendering
- **Headings:** H1–H6 with pyfiglet banners (optional)
- **Text:** paragraphs, lists (ul/ol), blockquotes, pre/code blocks
- **Links:** numbered display; clickable in both UIs
- **Tables:** colspan/rowspan support; min/preferred-width layout; rowspan height balancing
- **Forms:** interactive inputs (text, password, email, etc.) and buttons; GET/POST submission; responses loaded into viewport
- **Form Controls:** textarea, select/options, checkbox, radio, range, number, and date controls where supported by the UI
- **Layout:** terminal flex rows/columns with gap, justification, and wrapping
- **Images:** ASCII conversion (Pillow-based); optional ANSI 256-color dithering; disk cache
- **Media:** image embedding; optional asynchronous PyAV video decoding; unsupported video formats are reported explicitly
- **Styles:** color, font-weight, text-align, margins applied in ASCII rendering

### Textual TUI Controls
- `Ctrl+L`: focus URL bar
- `Enter`: load URL (when URL bar focused)
- `Alt+Left` / `Alt+Right`: back/forward history
- `1`–`9`: follow numbered links
- `F12`: open DOM/CSS/NETWORK/MEDIA/CONSOLE diagnostics
- `Alt+Q`: quit immediately
- `Ctrl+C`: quit confirmation with a session-level “Never ask me again” option
- Mouse: click links or interact with form inputs/buttons

### Tkinter GUI Controls
- **URL Bar:** enter and submit URLs
- **Back / Forward:** navigate history
- **Links:** click blue underlined links
- **Forms:** fill input fields and click buttons
- **Scrolling:** mouse wheel or scrollbar
- **Embedded Widgets:** forms render with native Tkinter inputs and buttons
- **Quit:** `Alt+Q` quits immediately; `Ctrl+C` opens confirmation with a “Never ask me again” option

## Phases Completed

- ✅ Phase 1: URL fetch + HTML parsing + basic ASCII rendering
- ✅ Phase 2: Textual TUI + scrolling + clickable links + history
- ✅ Phase 3: CSS parser + computed styles + layout
- ✅ Phase 4: tables, forms, images (4.1–4.5 complete)
- ✅ Phase 5: audio/video metadata
- ✅ Tkinter UI: full-featured GUI (links, forms, scrolling, history)

## Pending

- ✅ Phase 6: GET page caching, cache diagnostics, and deterministic cache tests
- ✅ Phase 7 supported slice: selectors, flex layout, practical controls, image embedding, diagnostics, and capability-gated media/script support

## Architecture

- **`nato_browser/network/http.py`**: Fetch URLs (GET/POST)
- **`nato_browser/html/parser.py`** + **`dom.py`**: HTML → DOM tree
- **`nato_browser/css/parser.py`** + **`styles.py`**: CSS parsing, style computation
- **`nato_browser/rendering/ascii.py`**: DOM → ASCII text (+ links, controls metadata)
- **`nato_browser/rendering/images.py`**: Image fetch + ASCII conversion + disk cache
- **`nato_browser/ui/app.py`**: Textual-based TUI + form submission handling
- **`nato_browser/ui/tkinter_app.py`**: Tkinter-based GUI (NEW)
- **`nato_browser/main.py`**: Entry points for both UIs
- **`test_phase6.py`**: Deterministic page-cache regression tests
- **`nato_browser/css/selectors.py`**: Simplified selector parser, matcher, and cascade
- **`nato_browser/media/video.py`**: Optional asynchronous PyAV decoder and playback controls
- **`nato_browser/scripting/engine.py`**: Safe JavaScript execution abstraction
- **`nato_browser/debugging/model.py`**: Shared DOM/network/media/console diagnostics

## Notes

- Image rendering requires Pillow; without it, images show placeholders.
- Video playback requires the optional PyAV backend and UI integration; unsupported formats are reported without crashing. DRM is never bypassed.
- JavaScript uses an inert engine by default; webpage code is never executed with Python access.
- The Textual `F12` panel displays DOM, CSS, NETWORK, MEDIA, and CONSOLE diagnostics.
- Table layout uses heuristic solver; CSS table properties (e.g., `table-layout: fixed`) are not yet supported.
- Form submission (POST) fetches and renders response in TUI/GUI; multipart/file uploads not yet supported.
- Image disk cache stored in system temp directory (e.g., `C:\Users\{user}\AppData\Local\Temp\nato_browser_cache`).
- Tkinter GUI requires Python with Tkinter support (usually included in standard Python installers).


