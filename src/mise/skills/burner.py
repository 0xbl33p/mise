from __future__ import annotations

import asyncio

from rich.console import Console

from mise.core.module import Module
from mise.core.skill import skill
from mise.core.stream import Out
from mise.messages import PlugTelemetry

console = Console()

MAX_WATTS = 1800.0  # typical US induction / hotplate ceiling


class BurnerModule(Module):
    """Wraps the smart plug controlling the burner. In sim mode this just prints + publishes
    the resulting PlugTelemetry so SimStove responds. In real mode this would hit a Shelly /
    Kasa HTTP endpoint."""

    telemetry = Out(PlugTelemetry)

    def __init__(self) -> None:
        super().__init__()
        self.percent = 0
        self.on = False

    async def run(self) -> None:
        while True:
            await self.telemetry.publish(
                PlugTelemetry(watts=self._watts(), on=self.on)
            )
            await asyncio.sleep(1.0)

    def _watts(self) -> float:
        return (self.percent / 100.0) * MAX_WATTS if self.on else 0.0

    @skill
    async def set_burner_percent(self, percent: int) -> str:
        """Set the burner power between 0 and 100 percent. 0 turns the burner off."""
        percent = max(0, min(100, int(percent)))
        self.percent = percent
        self.on = percent > 0
        console.log(f"[burner] -> {percent}% ({self._watts():.0f}W, on={self.on})")
        await self.telemetry.publish(PlugTelemetry(watts=self._watts(), on=self.on))
        return f"burner set to {percent}%"

    @skill
    async def kill_power(self) -> str:
        """Cut power to the burner immediately. Use for any safety event."""
        self.percent = 0
        self.on = False
        console.log("[burner] !! KILL POWER")
        await self.telemetry.publish(PlugTelemetry(watts=0.0, on=False))
        return "power cut"
