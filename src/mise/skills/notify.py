from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Awaitable, Callable

from rich.console import Console

from mise.core.module import Module
from mise.core.skill import skill

if TYPE_CHECKING:
    from mise.audio.gate import AudioGate

console = Console()

SpeakHook = Callable[[str], Awaitable[None]]


class NotifyModule(Module):
    """User-facing notifications with three optional output sinks:

    1. Console (always on) — prints the message with rich formatting.
    2. Local TTS via pyttsx3 — opt-in by passing an AudioGate.
    3. External hook (browser WS, Twilio, ...) — opt-in by passing on_speak / on_text.
    """

    def __init__(
        self,
        audio_gate: "AudioGate | None" = None,
        on_speak: SpeakHook | None = None,
        on_text: SpeakHook | None = None,
    ) -> None:
        super().__init__()
        self.audio_gate = audio_gate
        self.on_speak = on_speak
        self.on_text = on_text
        self._engine = None
        if audio_gate is not None:
            import pyttsx3  # noqa: PLC0415  (optional dep)

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 185)

    async def run(self) -> None:
        while True:
            await asyncio.sleep(3600)

    @skill
    async def speak(self, message: str) -> str:
        """Say something out loud to the user via the kitchen speaker."""
        console.print(f"[bold cyan][speak][/bold cyan] {message}")
        if self.on_speak is not None:
            try:
                await self.on_speak(message)
            except Exception as e:  # noqa: BLE001
                console.log(f"[notify] on_speak hook failed: {e}")
        if self._engine is not None and self.audio_gate is not None:
            loop = asyncio.get_event_loop()
            self.audio_gate.mark_tts_start()
            try:
                await loop.run_in_executor(None, self._speak_blocking, message)
            finally:
                self.audio_gate.mark_tts_end()
        return "spoken"

    def _speak_blocking(self, message: str) -> None:
        assert self._engine is not None
        self._engine.say(message)
        self._engine.runAndWait()

    @skill
    async def text_user(self, message: str) -> str:
        """Send a text message to the user's phone. Use when they've left the kitchen."""
        console.print(f"[bold magenta][text][/bold magenta] {message}")
        if self.on_text is not None:
            try:
                await self.on_text(message)
            except Exception as e:  # noqa: BLE001
                console.log(f"[notify] on_text hook failed: {e}")
        return "sent"
