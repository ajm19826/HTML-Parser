"""Capability-boundary tests for media and JavaScript."""
from nato_browser.html.parser import DOMBuilder
from nato_browser.rendering.ascii import render_dom
from nato_browser.scripting import NullJavaScriptEngine, create_javascript_engine


def test_video_without_decoder_is_explicitly_unsupported():
    builder = DOMBuilder()
    builder.feed("<video><source src='clip.mp4' type='video/mp4'></video>")
    rendered, _, _ = render_dom(builder.root)
    assert "Video format unsupported" in rendered


def test_javascript_defaults_to_safe_inert_engine():
    engine = create_javascript_engine()
    assert isinstance(engine, NullJavaScriptEngine)
    assert engine.execute("document.body.innerHTML = 'unsafe'")["status"] == "unsupported"


def test_video_player_requires_optional_decoder():
    from nato_browser.media.video import VideoPlaybackError, VideoPlayer
    player = VideoPlayer("missing.mp4")
    try:
        player.probe()
    except VideoPlaybackError:
        pass
    else:
        raise AssertionError("missing optional decoder should not be treated as playback support")
