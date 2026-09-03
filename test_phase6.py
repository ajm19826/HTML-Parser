"""Deterministic Phase 6 tests for page caching."""
from unittest.mock import Mock, patch

from nato_browser.network import http


def response(url="https://example.test/"):
    result = Mock()
    result.url = url
    result.text = "<html><body>cached</body></html>"
    result.headers = {"content-type": "text/html"}
    result.status_code = 200
    return result


def setup_function():
    http.clear_cache()


def test_identical_get_is_cached():
    with patch("requests.get", return_value=response()) as get:
        first = http.fetch("https://example.test")
        second = http.fetch("https://example.test")

    assert first == second
    assert get.call_count == 1


def test_force_refresh_bypasses_cache():
    with patch("requests.get", return_value=response()) as get:
        http.fetch("https://example.test")
        http.fetch("https://example.test", force_refresh=True)

    assert get.call_count == 2


def test_non_get_requests_bypass_cache():
    with patch("requests.request", return_value=response()) as request:
        http.fetch("https://example.test", method="POST", data={"q": "one"})
        http.fetch("https://example.test", method="POST", data={"q": "one"})

    assert request.call_count == 2


def test_authenticated_get_is_not_cached():
    with patch("requests.get", return_value=response()) as get:
        http.fetch("https://example.test", headers={"Authorization": "Bearer token"})
        http.fetch("https://example.test", headers={"Authorization": "Bearer token"})

    assert get.call_count == 2


def test_failed_response_is_not_cached():
    failed = response()
    failed.status_code = 500
    with patch("requests.get", return_value=failed) as get:
        http.fetch("https://example.test")
        http.fetch("https://example.test")

    assert get.call_count == 2


def test_cache_info_and_clear():
    with patch("requests.get", return_value=response()):
        http.fetch("https://example.test")

    assert http.cache_info()["entries"] == 1
    http.clear_cache()
    assert http.cache_info()["entries"] == 0
