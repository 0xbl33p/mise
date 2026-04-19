from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from rich.console import Console

from mise.core.module import Module
from mise.core.stream import In
from mise.messages import AudioEvent, StoveFrame
from mise.skills.burner import BurnerModule
from mise.skills.notify import NotifyModule

console = Console()


class StubAgent(Module):
    """Rule-based placeholder for the real Claude-driven agent.

    Wiring the real LLM in is a drop-in replacement: same inputs (StoveFrame, AudioEvent,
    UserUtterance), same skills (BurnerModule, NotifyModule). This stub proves the loop
    end-to-end before we pay the API.
    """

    frames_in = In(StoveFrame)
    audio_in = In(AudioEvent)

    def __init__(self, burner: BurnerModule, notify: NotifyModule) -> None:
        super().__init__()
        self.burner = burner
        self.notify = notify
        self._last_hot_ts: datetime | None = None
        self._smoke_warned = False
        self._user_present_until: datetime = datetime.now() + timedelta(seconds=20)

    async def run(self) -> None:
        await asyncio.gather(self._watch_frames(), self._watch_audio())

    async def _watch_frames(self) -> None:
        while True:
            frame: StoveFrame = await self.frames_in.get()
            console.log(
                f"[agent] frame t={frame.pan_temp_c:.1f}C  '{frame.contents}'"
            )

            if frame.pan_temp_c >= 180:
                self._last_hot_ts = frame.ts

            if frame.pan_temp_c >= 230 and not self._smoke_warned:
                self._smoke_warned = True
                await self.notify.speak("Oil is smoking — cut the heat now.")
                await self.burner.set_burner_percent(40)

            if self._last_hot_ts and frame.ts > self._user_present_until:
                away_for = frame.ts - self._user_present_until
                if away_for.total_seconds() > 10:
                    await self.notify.text_user(
                        f"You left the stove hot ({frame.pan_temp_c:.0f}C). "
                        "Cutting power."
                    )
                    await self.burner.kill_power()
                    self._user_present_until = frame.ts + timedelta(days=1)

    async def _watch_audio(self) -> None:
        while True:
            evt: AudioEvent = await self.audio_in.get()
            if evt.kind == "smoke_alarm":
                await self.burner.kill_power()
                await self.notify.speak("Smoke alarm triggered. Power cut.")
