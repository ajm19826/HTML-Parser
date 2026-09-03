"""ANSI color utilities for terminal rendering."""
from __future__ import annotations

# ANSI color codes
RESET = "\x1b[0m"

# Text formatting
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITALIC = "\x1b[3m"
UNDERLINE = "\x1b[4m"

# Foreground colors (basic)
BLACK = "\x1b[30m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
WHITE = "\x1b[37m"

# Bright foreground colors
BRIGHT_BLACK = "\x1b[90m"
BRIGHT_RED = "\x1b[91m"
BRIGHT_GREEN = "\x1b[92m"
BRIGHT_YELLOW = "\x1b[93m"
BRIGHT_BLUE = "\x1b[94m"
BRIGHT_MAGENTA = "\x1b[95m"
BRIGHT_CYAN = "\x1b[96m"
BRIGHT_WHITE = "\x1b[97m"

# Background colors
BG_BLACK = "\x1b[40m"
BG_RED = "\x1b[41m"
BG_GREEN = "\x1b[42m"
BG_YELLOW = "\x1b[43m"
BG_BLUE = "\x1b[44m"
BG_MAGENTA = "\x1b[45m"
BG_CYAN = "\x1b[46m"
BG_WHITE = "\x1b[47m"

# 256-color support
def fg256(code: int) -> str:
    """Return 256-color foreground code."""
    return f"\x1b[38;5;{code}m"

def bg256(code: int) -> str:
    """Return 256-color background code."""
    return f"\x1b[48;5;{code}m"

def rgb(r: int, g: int, b: int, bg: bool = False) -> str:
    """Return RGB truecolor code (24-bit)."""
    prefix = "48" if bg else "38"
    return f"\x1b[{prefix};2;{r};{g};{b}m"


# CSS color name to ANSI mapping
CSS_COLOR_MAP = {
    "red": RED,
    "blue": BLUE,
    "green": GREEN,
    "yellow": YELLOW,
    "magenta": MAGENTA,
    "cyan": CYAN,
    "black": BLACK,
    "white": WHITE,
    "darkred": "\x1b[31m",
    "darkblue": "\x1b[34m",
    "darkgreen": "\x1b[32m",
    "orange": BRIGHT_YELLOW,
    "purple": MAGENTA,
    "pink": BRIGHT_MAGENTA,
    "gray": "\x1b[90m",
    "grey": "\x1b[90m",
    "lightgray": BRIGHT_BLACK,
    "lightgrey": BRIGHT_BLACK,
}


def colorize(text: str, **styles) -> str:
    """Apply ANSI styles to text.
    
    Args:
        text: Text to colorize
        color: CSS color name or hex color
        background: Background color
        bold: Apply bold
        underline: Apply underline
        dim: Apply dim
    
    Returns:
        Text with ANSI codes applied
    """
    codes = []
    
    if styles.get("bold"):
        codes.append(BOLD)
    if styles.get("underline"):
        codes.append(UNDERLINE)
    if styles.get("dim"):
        codes.append(DIM)
    if styles.get("italic"):
        codes.append(ITALIC)
    
    color = styles.get("color")
    if color:
        color_lower = str(color).lower().strip()
        if color_lower in CSS_COLOR_MAP:
            codes.append(CSS_COLOR_MAP[color_lower])
        elif color_lower.startswith("#"):
            # Convert hex to RGB
            hex_str = color_lower.lstrip("#")
            try:
                if len(hex_str) == 6:
                    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                    codes.append(rgb(r, g, b))
            except (ValueError, IndexError):
                pass
        elif color_lower.startswith("rgb"):
            # Parse rgb(...) or rgba(...)
            try:
                parts = color_lower.replace("rgb(", "").replace("rgba(", "").replace(")", "").split(",")
                if len(parts) >= 3:
                    r = int(parts[0].strip())
                    g = int(parts[1].strip())
                    b = int(parts[2].strip())
                    codes.append(rgb(r, g, b))
            except (ValueError, IndexError):
                pass
    
    bg_color = styles.get("background")
    if bg_color:
        bg_lower = str(bg_color).lower().strip()
        if bg_lower.startswith("#"):
            hex_str = bg_lower.lstrip("#")
            try:
                if len(hex_str) == 6:
                    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                    codes.append(rgb(r, g, b, bg=True))
            except (ValueError, IndexError):
                pass
    
    if not codes:
        return text
    
    return "".join(codes) + text + RESET
