from __future__ import annotations

import asyncio
import random

from rich.console import Console

from mise.core.module import Module
from mise.core.stream import In, Out
from mise.messages import AudioEvent, PlugTelemetry, StoveFrame
from mise.perception.pan_render import render_pan_b64

console = Console()


class SimStove(Module):
    """Synthetic kitchen: pretends the pan is heating up, makes noise as it does.

    The burner level is driven by the BurnerModule (via PlugTelemetry it publishes).
    This module reads that level and evolves pan temperature toward a setpoint implied
    by watts. When temp crosses thresholds, it emits audio events and writes a
    plain-English "contents" string the agent/VLM stand-in can reason about.
    """

    frames = Out(StoveFrame)
    audio = Out(AudioEvent)
    plug_in = In(PlugTelemetry)

    def __init__(
        self,
        tick_seconds: float = 1.0,
        ambient_c: float = 22.0,
        render_images: bool = False,
        image_size: int = 256,
    ) -> None:
        super().__init__()
        self.tick = tick_seconds
        self.temp_c = ambient_c
        self.ambient = ambient_c
        self.watts = 0.0
        self.on = False
        self.render_images = render_images
        self.image_size = image_size

    async def _consume_plug(self) -> None:
        while True:
            msg: PlugTelemetry = await self.plug_in.get()
            self.watts = msg.watts
            self.on = msg.on

    async def run(self) -> None:
        asyncio.create_task(self._consume_plug())
        while True:
            await asyncio.sleep(self.tick)

            if self.on:
                target = 25.0 + self.watts * 0.12
                self.temp_c += (target - self.temp_c) * 0.18
            else:
                self.temp_c += (self.ambient - self.temp_c) * 0.05

            jitter = random.uniform(-1.5, 1.5)
            self.temp_c = max(self.ambient, self.temp_c + jitter)

            contents = self._describe()
            image_b64 = (
                render_pan_b64(self.temp_c, size=self.image_size)
                if self.render_images
                else None
            )
            await self.frames.publish(
                StoveFrame(
                    pan_temp_c=round(self.temp_c, 1),
                    contents=contents,
                    image_b64=image_b64,
                )
            )

            event = self._sound_for_temp()
            if event is not None:
                await self.audio.publish(AudioEvent(kind=event))

    def _describe(self) -> str:
        if self.temp_c < 60:
            return "cold pan, food sitting"
        if self.temp_c < 120:
            return "pan warming, mild steam"
        if self.temp_c < 180:
            return "food actively cooking, steam rising"
        if self.temp_c < 230:
            return "browning edges, light smoke forming"
        return "heavy smoke, oil smoking, food charring"

    def _sound_for_temp(self) -> str | None:
        if self.temp_c >= 230:
            return "smoke_alarm" if random.random() < 0.3 else "oil_crackle"
        if self.temp_c >= 150:
            return "sizzle" if random.random() < 0.6 else None
        if self.temp_c >= 100:
            return "boil" if random.random() < 0.3 else None
        return None
