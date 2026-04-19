from __future__ import annotations

import time


class AudioGate:
    """Shared state between TTS (NotifyModule.speak) and mic (MicVoice).

    While the speaker is emitting, the mic drops frames to avoid transcribing our own TTS.
    A short tail after tts_end blocks lingering room echo.
    """

    def __init__(self, echo_tail_s: float = 0.5) -> None:
        self._tts_until: float = 0.0
        self._echo_tail_s = echo_tail_s

    def mark_tts_start(self) -> None:
        self._tts_until = float("inf")

    def mark_tts_end(self) -> None:
        self._tts_until = time.monotonic() + self._echo_tail_s

    def mic_should_drop(self) -> bool:
        return time.monotonic() < self._tts_until
