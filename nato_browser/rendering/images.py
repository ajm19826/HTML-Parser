"""Helpers for downloading images and converting to ASCII art (best-effort)."""
from __future__ import annotations

import hashlib
import os
import tempfile
from io import BytesIO
from typing import List
from functools import lru_cache


# Enhanced character ramp for better tonal representation
CHAR_RAMP = "@%#*+=-:;.  "


def _get_disk_cache_path() -> str:
    """Get the disk cache directory for images."""
    cache_dir = os.path.join(tempfile.gettempdir(), "nato_browser_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _cache_key_from_url(url: str, width: int) -> str:
    """Generate a cache key for URL + width."""
    data = f"{url}:{width}".encode()
    return hashlib.sha256(data).hexdigest()


def fetch_image_bytes(url: str, timeout: int = 10, use_disk_cache: bool = True) -> bytes | None:
    """Fetch image bytes from URL; optionally use disk cache."""
    if use_disk_cache:
        cache_dir = _get_disk_cache_path()
        cache_file = os.path.join(cache_dir, hashlib.sha256(url.encode()).hexdigest())
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    return f.read()
            except Exception:
                pass
    
    data = None
    try:
        import requests

        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.content
    except Exception:
        try:
            from urllib.request import urlopen, Request

            req = Request(url, headers={"User-Agent": "NATO-ASCII-Browser/0.1"})
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
        except Exception:
            pass
    
    # cache to disk if successful
    if data and use_disk_cache:
        try:
            cache_dir = _get_disk_cache_path()
            cache_file = os.path.join(cache_dir, hashlib.sha256(url.encode()).hexdigest())
            with open(cache_file, "wb") as f:
                f.write(data)
        except Exception:
            pass
    
    return data


def image_bytes_to_ascii(data: bytes, width: int = 40, use_color: bool = False) -> List[str]:
    """Convert image bytes to ASCII art with optional color dithering."""
    try:
        from PIL import Image

        img = Image.open(BytesIO(data))
        # convert to grayscale and resize preserving aspect ratio
        w, h = img.size
        aspect = h / w if w else 1
        new_w = max(1, min(width, w))
        new_h = max(1, int(aspect * new_w * 0.5))
        img = img.convert("L").resize((new_w, new_h))
        pixels = list(img.getdata())
        
        if use_color:
            # Optional: use ANSI 256-color with a simple dithering approach
            return _ascii_with_color(pixels, new_w, new_h)
        else:
            # Grayscale ASCII with tuned ramp
            out_lines = []
            for row in range(new_h):
                line = ""
                for col in range(new_w):
                    val = pixels[row * new_w + col]
                    idx = int((val / 255) * (len(CHAR_RAMP) - 1))
                    line += CHAR_RAMP[idx]
                out_lines.append(line)
            return out_lines
    except Exception:
        return []


def _ascii_with_color(pixels: List[int], width: int, height: int) -> List[str]:
    """Convert pixels to ANSI 256-color ASCII with simple dithering."""
    # Map grayscale to ANSI 256-color codes (grayscale block: 232-255)
    # 232-255 is a 24-step grayscale in ANSI 256-color
    out_lines = []
    for row in range(height):
        line = ""
        for col in range(width):
            val = pixels[row * width + col]
            # map 0-255 to grayscale codes 232-255 (24 levels)
            code = 232 + int((val / 255) * 23)
            # use a dense char and color it
            char = "█"  # full block
            line += f"\x1b[38;5;{code}m{char}\x1b[0m"
        out_lines.append(line)
    return out_lines


@lru_cache(maxsize=128)
def get_ascii_for_url(url: str, width: int = 40, use_color: bool = False) -> List[str]:
    """Get ASCII art for URL with LRU cache and optional disk cache."""
    data = fetch_image_bytes(url, use_disk_cache=True)
    if not data:
        return []
    return image_bytes_to_ascii(data, width=width, use_color=use_color)
