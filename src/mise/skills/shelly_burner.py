from __future__ import annotations

import asyncio

import httpx
from rich.console import Console

from mise.core.module import Module
from mise.core.skill import skill
from mise.core.stream import Out
from mise.messages import PlugTelemetry, SafetyAlert

console = Console()

# Shelly Plus Plug US speaks Gen2 RPC: https://shelly-api-docs.shelly.cloud/gen2/
# The plug is a single-channel relay at switch id=0. It can report power draw but it
# cannot dim — it's binary on/off. set_burner_percent(>0) therefore maps to "on",
# and intermediate heat levels must be spoken requests to the user.


IDLE_WATTS = 50.0  # anything above this while "off" is a live load
DISCREPANCY_TICKS = 2  # consecutive bad polls before we yell


class ShellyBurner(Module):
    """Real Shelly Plus Plug US driver. Same skill interface as the sim BurnerModule."""

    telemetry = Out(PlugTelemetry)
    alerts = Out(SafetyAlert)

    def __init__(
        self,
        host: str,
        poll_interval_s: float = 1.5,
        request_timeout_s: float = 2.0,
    ) -> None:
        super().__init__()
        self.host = host.rstrip("/")
        self.poll_interval = poll_interval_s
        self.timeout = request_timeout_s
        self._client = httpx.AsyncClient(
            base_url=f"http://{self.host}",
            timeout=self.timeout,
        )
        self._last_watts: float = 0.0
        self._last_on: bool = False
        self._reachable: bool | None = None
        self._desired_on: bool = False
        self._discrepancy_ticks: int = 0
        self._unreachable_warned: bool = False

    async def run(self) -> None:
        # Probe once up front for a clear reachability log line.
        await self._probe_once()
        while True:
            try:
                r = await self._client.get("/rpc/Switch.GetStatus", params={"id": 0})
                r.raise_for_status()
                data = r.json()
                self._last_watts = float(data.get("apower", 0.0))
                self._last_on = bool(data.get("output", False))
                if self._reachable is not True:
                    console.log(f"[shelly {self.host}] reachable")
                    self._reachable = True
                    self._unreachable_warned = False
                await self._check_discrepancy()
            except Exception as e:  # noqa: BLE001
                if self._reachable is not False:
                    console.log(f"[shelly {self.host}] unreachable: {e}")
                    self._reachable = False
                self._last_watts = 0.0
                self._last_on = False
                # If power is desired on but the plug can't be reached during a cook
                # session, raise an alert once to avoid spamming.
                if self._desired_on and not self._unreachable_warned:
                    self._unreachable_warned = True
                    await self.alerts.publish(
                        SafetyAlert(
                            kind="plug_unreachable",
                            detail=(
                                f"Lost contact with the smart plug at {self.host}. "
                                "I can't confirm whether the burner is actually on or off."
                            ),
                        )
                    )
            await self.telemetry.publish(
                PlugTelemetry(watts=self._last_watts, on=self._last_on)
            )
            await asyncio.sleep(self.poll_interval)

    async def _check_discrepancy(self) -> None:
        """If we commanded off but the plug still draws power, something's stuck."""
        if not self._desired_on and (self._last_on or self._last_watts > IDLE_WATTS):
            self._discrepancy_ticks += 1
            if self._discrepancy_ticks == DISCREPANCY_TICKS:
                await self.alerts.publish(
                    SafetyAlert(
                        kind="power_after_kill",
                        detail=(
                            f"I told the plug to cut power, but it still reports "
                            f"{self._last_watts:.0f}W and output={self._last_on}. "
                            "The relay may be stuck — unplug the cord manually."
                        ),
                    )
                )
        else:
            self._discrepancy_ticks = 0

    async def _probe_once(self) -> None:
        try:
            r = await self._client.get("/rpc/Shelly.GetDeviceInfo")
            r.raise_for_status()
            info = r.json()
            console.log(
                f"[shelly {self.host}] connected — {info.get('name') or info.get('id')}"
                f" ({info.get('model', '?')})"
            )
            self._reachable = True
        except Exception as e:  # noqa: BLE001
            console.log(
                f"[shelly {self.host}] not reachable yet: {e} — will keep retrying "
                "each poll; set_burner_percent / kill_power will still be accepted."
            )
            self._reachable = False

    async def _set_output(self, on: bool) -> bool:
        """Flip the relay. Returns True on success, False if the plug is unreachable."""
        try:
            r = await self._client.get(
                "/rpc/Switch.Set", params={"id": 0, "on": "true" if on else "false"}
            )
            r.raise_for_status()
            return True
        except Exception as e:  # noqa: BLE001
            console.log(f"[shelly {self.host}] switch call failed: {e}")
            return False

    @skill
    async def set_burner_percent(self, percent: int) -> str:
        """Set the burner power. On a real smart plug this is binary: 0 = off, any other \
value = on. For intermediate heat levels, also call `speak` to ask the user to adjust \
the burner's own dial."""
        percent = max(0, min(100, int(percent)))
        want_on = percent > 0
        self._desired_on = want_on
        self._discrepancy_ticks = 0  # reset the safety counter on a fresh command
        ok = await self._set_output(want_on)
        self._last_on = want_on
        await self.telemetry.publish(
            PlugTelemetry(watts=self._last_watts if want_on else 0.0, on=want_on)
        )
        if not ok:
            return f"plug unreachable (would have set to {'on' if want_on else 'off'})"
        return f"plug {'on' if want_on else 'off'} (requested {percent}%)"

    @skill
    async def kill_power(self) -> str:
        """Cut power to the burner immediately. Use for any safety event."""
        self._desired_on = False
        self._discrepancy_ticks = 0
        ok = await self._set_output(False)
        self._last_on = False
        await self.telemetry.publish(PlugTelemetry(watts=0.0, on=False))
        return "power cut" if ok else "plug unreachable — power cut NOT confirmed"
