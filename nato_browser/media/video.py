"""Optional asynchronous video decoding for terminal playback.

PyAV is deliberately optional. No decoder or DRM bypass is attempted when it is
not installed or when the source cannot be decoded.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterator


class VideoPlaybackError(RuntimeError):
    """Raised when a video cannot be decoded or played."""


def video_playback_available() -> bool:
    try:
        import av  # noqa: F401
        return True
    except ImportError:
        return False


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float | None
    audio_available: bool


class VideoPlayer:
    """Decode video frames on a worker thread with bounded buffering.

    Audio output is exposed as a capability. PyAV decoding alone does not route
    samples to the operating system, so an audio backend must be supplied by a
    UI integration rather than silently discarding or pretending to play audio.
    """

    def __init__(self, source: str, target_fps: float = 8.0, max_buffer: int = 8):
        self.source = source
        self.target_fps = max(1.0, target_fps)
        self.frames: queue.Queue = queue.Queue(maxsize=max(1, max_buffer))
        self.paused = threading.Event()
        self.stopped = threading.Event()
        self.paused.set()
        self.thread: threading.Thread | None = None
        self.position = 0.0
        self.duration: float | None = None
        self.muted = False
        self.volume = 1.0
        self.info: VideoInfo | None = None

    def probe(self) -> VideoInfo:
        try:
            import av
        except ImportError as exc:
            raise VideoPlaybackError("PyAV is not installed") from exc
        try:
            container = av.open(self.source)
            stream = next(stream for stream in container.streams if stream.type == "video")
            fps = float(stream.average_rate) if stream.average_rate else 30.0
            duration = float(stream.duration * stream.time_base) if stream.duration else None
            self.info = VideoInfo(
                width=stream.codec_context.width,
                height=stream.codec_context.height,
                fps=fps,
                duration=duration,
                audio_available=any(item.type == "audio" for item in container.streams),
            )
            self.duration = duration
            container.close()
            return self.info
        except Exception as exc:
            raise VideoPlaybackError(f"Video format unsupported: {exc}") from exc

    def play(self, on_frame: Callable[[object, float], None]) -> None:
        if self.thread and self.thread.is_alive():
            self.paused.clear()
            return
        self.stopped.clear()
        self.paused.clear()
        self.thread = threading.Thread(target=self._decode, args=(on_frame,), daemon=True)
        self.thread.start()

    def pause(self) -> None:
        self.paused.set()

    def stop(self) -> None:
        self.stopped.set()
        self.paused.clear()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=1.0)

    def seek(self, seconds: float) -> None:
        self.position = max(0.0, seconds)

    def set_muted(self, muted: bool) -> None:
        self.muted = muted

    def set_volume(self, volume: float) -> None:
        self.volume = min(1.0, max(0.0, volume))

    def _decode(self, on_frame: Callable[[object, float], None]) -> None:
        try:
            import av
            container = av.open(self.source)
            stream = next(stream for stream in container.streams if stream.type == "video")
            start = self.position
            for frame in container.decode(stream):
                if self.stopped.is_set():
                    break
                timestamp = float(frame.time or 0.0)
                if timestamp < start:
                    continue
                while self.paused.wait(timeout=0.1):
                    if self.stopped.is_set():
                        break
                if self.stopped.is_set():
                    break
                on_frame(frame, timestamp)
                self.position = timestamp
                time.sleep(1.0 / self.target_fps)
            container.close()
        except Exception as exc:
            self.stopped.set()
            raise VideoPlaybackError(f"Video playback failed: {exc}") from exc


def frames_to_ascii(frame, width: int = 80, use_color: bool = False) -> list[str]:
    """Convert one decoded PyAV frame to terminal ASCII without retaining it."""
    try:
        image = frame.to_image()
        from nato_browser.rendering.images import image_bytes_to_ascii
        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return image_bytes_to_ascii(buffer.getvalue(), width=width, use_color=use_color)
    except Exception as exc:
        raise VideoPlaybackError(f"Frame conversion failed: {exc}") from exc
