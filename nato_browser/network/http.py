"""Simple HTTP fetcher with safe defaults."""
from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict
from typing import Tuple, Optional, Any
from urllib.parse import urlencode
from nato_browser.debugging import debug_session

DEFAULT_TIMEOUT = 10
MAX_BODY_BYTES = 5_000_000
CACHE_MAX_ENTRIES = 64
CACHE_TTL = 300.0

_logger = logging.getLogger("nato_browser.network")
_page_cache: OrderedDict[tuple, tuple] = OrderedDict()


def clear_cache() -> None:
    """Clear cached GET responses."""
    _page_cache.clear()


def cache_info() -> dict:
    """Return lightweight page-cache statistics."""
    return {"entries": len(_page_cache), "max_entries": CACHE_MAX_ENTRIES, "ttl": CACHE_TTL}


def _cache_key(url: str, headers: Optional[dict]) -> tuple:
    normalized_headers = tuple(sorted((str(k).lower(), str(v)) for k, v in (headers or {}).items()))
    return url, normalized_headers


def _cache_allowed(method: str, headers: Optional[dict]) -> bool:
    if method.upper() != "GET":
        return False
    restricted = {str(k).lower() for k in (headers or {})}
    return not restricted.intersection({"authorization", "cookie"})


def _debug_enabled() -> bool:
    return os.environ.get("NATO_BROWSER_DEBUG", "").lower() in {"1", "true", "yes", "on"}


def fetch(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    method: str = "GET",
    data: Optional[Any] = None,
    headers: Optional[dict] = None,
    *,
    use_cache: bool = True,
    force_refresh: bool = False,
    cache_ttl: float = CACHE_TTL,
) -> Tuple[str, str, dict, int]:
    """Fetch URL and return (final_url, text, headers, status_code).

    Uses requests if available, otherwise urllib as a fallback.
    """
    method_upper = method.upper()
    timeout = min(max(0.1, float(timeout)), float(DEFAULT_TIMEOUT))
    started = time.perf_counter()
    deadline = started + timeout
    can_cache = use_cache and _cache_allowed(method_upper, headers)
    key = _cache_key(url, headers) if can_cache else None
    now = time.monotonic()
    if can_cache and not force_refresh and key in _page_cache:
        cached_at, cached_value = _page_cache[key]
        if now - cached_at < max(0.0, cache_ttl):
            _page_cache.move_to_end(key)
            if _debug_enabled():
                _logger.info("GET cache hit url=%s elapsed_ms=%.1f", url, (time.perf_counter() - started) * 1000)
            return cached_value
        del _page_cache[key]

    result = None
    try:
        import requests
        remaining = max(0.1, deadline - time.perf_counter())
        req_headers = headers or {}
        if method_upper == "GET":
            resp = requests.get(url, headers=req_headers, timeout=remaining)
        else:
            # assume form-encoded body when data is a dict
            if isinstance(data, dict):
                resp = requests.request(method_upper, url, data=data, headers=req_headers, timeout=remaining)
            else:
                resp = requests.request(method_upper, url, data=data, headers=req_headers, timeout=remaining)
        if resp.headers.get("content-length") and int(resp.headers["content-length"]) > MAX_BODY_BYTES:
            raise ValueError("Resource too large")
        content = resp.text
        if len(content.encode("utf-8", errors="replace")) > MAX_BODY_BYTES:
            raise ValueError("Resource too large")
        result = (resp.url, content, dict(resp.headers), resp.status_code)
    except Exception:
        # fallback to urllib
        try:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise TimeoutError("Request exceeded timeout")
            from urllib.request import urlopen, Request

            req_headers = {"User-Agent": "NATO-ASCII-Browser/0.1"}
            if headers:
                req_headers.update(headers)
            if method_upper == "GET":
                req = Request(url, headers=req_headers)
                with urlopen(req, timeout=remaining) as resp:
                    final = resp.geturl()
                    headers_ret = dict(resp.getheaders())
                    raw = resp.read(MAX_BODY_BYTES + 1)
                    if len(raw) > MAX_BODY_BYTES:
                        raise ValueError("Resource too large")
                    text = raw.decode(errors="replace")
                    result = (final, text, headers_ret, getattr(resp, "status", 200))
            else:
                # POST/PUT etc. send encoded data when dict
                body = None
                if isinstance(data, dict):
                    body = urlencode(data).encode()
                    req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                elif isinstance(data, (bytes, bytearray)):
                    body = data
                else:
                    body = str(data or "").encode()
                req = Request(url, data=body, headers=req_headers)
                req.get_method = lambda: method_upper  # type: ignore
                with urlopen(req, timeout=remaining) as resp:
                    final = resp.geturl()
                    headers_ret = dict(resp.getheaders())
                    raw = resp.read(MAX_BODY_BYTES + 1)
                    if len(raw) > MAX_BODY_BYTES:
                        raise ValueError("Resource too large")
                    text = raw.decode(errors="replace")
                    result = (final, text, headers_ret, getattr(resp, "status", 200))
        except Exception as e:
            result = (url, "", {}, 0)

    if can_cache and key is not None and result[3] in range(200, 400):
        _page_cache[key] = (time.monotonic(), result)
        _page_cache.move_to_end(key)
        while len(_page_cache) > CACHE_MAX_ENTRIES:
            _page_cache.popitem(last=False)
    if _debug_enabled():
        _logger.info(
            "fetch method=%s url=%s status=%s bytes=%s elapsed_ms=%.1f cache=%s",
            method_upper, url, result[3], len(result[1].encode("utf-8")),
            (time.perf_counter() - started) * 1000, "enabled" if can_cache else "bypassed",
        )
    debug_session.add_network(
        method=method_upper,
        url=url,
        status=result[3],
        bytes=len(result[1].encode("utf-8")),
        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        cache="enabled" if can_cache else "bypassed",
    )
    return result
