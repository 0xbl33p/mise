from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from rich.console import Console

from mise.core.module import Module
from mise.core.stream import In, Out
from mise.messages import CookPlanState, PlugTelemetry, SafetyAlert, StoveFrame, UserUtterance

console = Console()


class BrowserBridge(Module):
    """Owns the active WebSocket to the browser.

    Inbound (browser -> here -> module graph):
      - {"type": "frame", "image_b64": "..."}   -> publish StoveFrame
      - {"type": "utterance", "text": "..."}    -> publish UserUtterance

    Outbound (module graph -> here -> browser): this module subscribes to agent
    notifications (via NotifyModule.on_speak / on_text hooks) and burner/cook-plan
    telemetry streams, and forwards them to the active WebSocket client.
    """

    plug_in = In(PlugTelemetry)
    plan_in = In(CookPlanState)
    alert_in = In(SafetyAlert)
    frames_out = Out(StoveFrame)
    utter_out = Out(UserUtterance)

    def __init__(self) -> None:
        super().__init__()
        self._ws_lock = asyncio.Lock()
        self._ws = None  # set by the FastAPI handler when a client connects

    def set_socket(self, ws) -> None:  # noqa: ANN001 - fastapi WebSocket
        self._ws = ws

    def clear_socket(self) -> None:
        self._ws = None

    async def run(self) -> None:
        await asyncio.gather(self._pump_plug(), self._pump_plan(), self._pump_alerts())

    async def _send(self, payload: dict[str, Any]) -> None:
        ws = self._ws
        if ws is None:
            return
        async with self._ws_lock:
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception as e:  # noqa: BLE001
                console.log(f"[bridge] ws send failed: {e}")
                self._ws = None

    # ---- inbound from browser -----------------------------------------------

    async def on_browser_frame(self, image_b64: str) -> None:
        await self.frames_out.publish(
            StoveFrame(image_b64=image_b64, contents="", pan_temp_c=None)
        )

    async def on_browser_utterance(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        await self.utter_out.publish(UserUtterance(text=text))

    # ---- outbound to browser ------------------------------------------------

    async def on_agent_speak(self, message: str) -> None:
        await self._send({"type": "speak", "message": message, "ts": datetime.now().isoformat()})

    async def on_agent_text(self, message: str) -> None:
        await self._send({"type": "text", "message": message, "ts": datetime.now().isoformat()})

    async def _pump_plug(self) -> None:
        while True:
            msg: PlugTelemetry = await self.plug_in.get()
            await self._send(
                {"type": "burner", "watts": msg.watts, "on": msg.on, "ts": msg.ts.isoformat()}
            )

    async def _pump_plan(self) -> None:
        while True:
            msg: CookPlanState = await self.plan_in.get()
            payload: dict[str, Any] = {"type": "plan", "step_index": msg.step_index}
            if msg.plan is not None:
                payload["dish"] = msg.plan.dish
                payload["steps"] = [
                    {
                        "description": s.description,
                        "target_pan_c": s.target_pan_c,
                        "duration_s": s.duration_s,
                        "notes": s.notes,
                    }
                    for s in msg.plan.steps
                ]
            await self._send(payload)

    async def _pump_alerts(self) -> None:
        while True:
            a: SafetyAlert = await self.alert_in.get()
            await self._send(
                {
                    "type": "alert",
                    "kind": a.kind,
                    "detail": a.detail,
                    "ts": a.ts.isoformat(),
                }
            )
