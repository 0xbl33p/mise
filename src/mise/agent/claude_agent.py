from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from openai import AsyncOpenAI
from rich.console import Console

from mise.core.module import Module
from mise.core.skill import Skill, get_skills, skill_to_openai_tool
from mise.core.stream import In
from mise.messages import AudioEvent, CookPlanState, SafetyAlert, StoveFrame, UserUtterance

console = Console()

SYSTEM_PROMPT = """You are Mise, a kitchen safety + cooking copilot. You see the cooktop \
through a camera and hear it through a microphone. Your job:

1. Keep the user safe. If the pan is smoking, if oil crackles violently, or if the user \
has left the kitchen while the burner is on and hot, act immediately (reduce heat or \
cut power) and notify them.
2. Guide the cook. If the user has said what they're making, help with heat adjustments \
and step-by-step coaching through the `speak` skill. When there is an active cook plan, \
bias heat toward the current step's target_pan_c and advance the plan when the step is done.
3. Plan when asked. If the user asks what to make, what to cook, for a recipe, or says \
something like "I have X, Y, Z — walk me through it", call `ask_sous_chef` first, then \
pass the returned JSON to `start_cook_plan` to install it.
4. When an image of the cooktop is attached, trust your eyes over the text description. \
Look for steam (soft white, moves), smoke (grey, persistent), oil shimmer (glossy surface), \
browning / charring (darker patches). Mention what you see only when it changes your decision.
5. Remember. Call `recall` when the user asks about their cooking history ("have I made \
this before?", "how did it go last time?"). Don't fabricate memories — if recall returns \
"no relevant memories", say so.
6. Respond to safety alerts. When a SAFETY ALERT appears in your observation, treat it as \
the highest-priority input: tell the user about it via speak and take the safest action \
(kill_power, or if that's already failing, tell them to unplug the cord manually).
7. Be concise. One short sentence when you speak. Don't narrate every frame.

Call a tool only when action is warranted; silence is fine. If no action is needed, \
respond with an empty message and no tool call."""


@dataclass
class _AgentEvent:
    kind: str  # "frame" | "audio" | "utterance"
    payload: StoveFrame | AudioEvent | UserUtterance


@dataclass
class _State:
    last_frame: StoveFrame | None = None
    last_utterance: UserUtterance | None = None
    recent_audio: list[AudioEvent] = field(default_factory=list)
    plan_state: CookPlanState | None = None
    recent_alerts: list[SafetyAlert] = field(default_factory=list)
    last_llm_call: datetime = field(default_factory=lambda: datetime.min)
    last_llm_temp: float = -999.0


class ClaudeAgent(Module):
    """LLM-driven agent using OpenRouter (OpenAI-compatible API).

    Same stream contract as StubAgent, so it's a drop-in replacement. Rate-limits LLM calls
    using a simple heuristic: temp delta >10C, new audio event, new user utterance, or at
    most one call per `min_call_interval_s` seconds.
    """

    frames_in = In(StoveFrame)
    audio_in = In(AudioEvent)
    utter_in = In(UserUtterance)
    plan_in = In(CookPlanState)
    alert_in = In(SafetyAlert)

    def __init__(
        self,
        skill_modules: list[Module],
        model: str = "anthropic/claude-sonnet-4.6",
        min_call_interval_s: float = 4.0,
        max_history_turns: int = 12,
    ) -> None:
        super().__init__()
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. Put it in mise/.env or export it."
            )
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model
        self.min_call_interval = timedelta(seconds=min_call_interval_s)
        self.max_history_turns = max_history_turns

        self._skill_map: dict[str, Skill] = {}
        self._tools: list[dict] = []
        for mod in skill_modules:
            for s in get_skills(mod):
                self._skill_map[s.name] = s
                self._tools.append(skill_to_openai_tool(s))

        self._state = _State()
        self._events: asyncio.Queue[_AgentEvent] = asyncio.Queue(maxsize=256)
        self._history: list[dict] = []

    async def run(self) -> None:
        console.log(f"[claude-agent] model={self.model} tools={len(self._tools)}")
        await asyncio.gather(
            self._feed_frames(),
            self._feed_audio(),
            self._feed_utter(),
            self._feed_plan(),
            self._feed_alerts(),
            self._react_loop(),
        )

    async def _feed_frames(self) -> None:
        while True:
            f: StoveFrame = await self.frames_in.get()
            await self._events.put(_AgentEvent("frame", f))

    async def _feed_audio(self) -> None:
        while True:
            a: AudioEvent = await self.audio_in.get()
            await self._events.put(_AgentEvent("audio", a))

    async def _feed_utter(self) -> None:
        while True:
            u: UserUtterance = await self.utter_in.get()
            await self._events.put(_AgentEvent("utterance", u))

    async def _feed_plan(self) -> None:
        while True:
            p: CookPlanState = await self.plan_in.get()
            await self._events.put(_AgentEvent("plan", p))

    async def _feed_alerts(self) -> None:
        while True:
            a: SafetyAlert = await self.alert_in.get()
            await self._events.put(_AgentEvent("alert", a))

    async def _react_loop(self) -> None:
        while True:
            evt = await self._events.get()
            self._absorb(evt)
            if not self._should_call_llm(evt):
                continue
            try:
                await self._think()
            except Exception as e:  # noqa: BLE001
                console.log(f"[claude-agent] LLM error: {e}")

    def _absorb(self, evt: _AgentEvent) -> None:
        if evt.kind == "frame":
            self._state.last_frame = evt.payload  # type: ignore[assignment]
        elif evt.kind == "audio":
            self._state.recent_audio.append(evt.payload)  # type: ignore[arg-type]
            self._state.recent_audio = self._state.recent_audio[-8:]
        elif evt.kind == "utterance":
            self._state.last_utterance = evt.payload  # type: ignore[assignment]
        elif evt.kind == "plan":
            self._state.plan_state = evt.payload  # type: ignore[assignment]
        elif evt.kind == "alert":
            self._state.recent_alerts.append(evt.payload)  # type: ignore[arg-type]
            self._state.recent_alerts = self._state.recent_alerts[-4:]

    def _should_call_llm(self, evt: _AgentEvent) -> bool:
        now = datetime.now()
        if now - self._state.last_llm_call < self.min_call_interval:
            if evt.kind == "audio" and evt.payload.kind == "smoke_alarm":  # type: ignore[union-attr]
                pass  # always take smoke alarms immediately
            elif evt.kind == "alert":
                pass  # safety alerts always bypass the rate limit
            else:
                return False
        if evt.kind in ("audio", "utterance", "plan", "alert"):
            return True
        if evt.kind == "frame":
            f: StoveFrame = evt.payload  # type: ignore[assignment]
            if f.pan_temp_c is None:
                # No thermal data (browser mode) — let image deltas drive calls: any new
                # frame past the rate limit is worth a look.
                return True
            if abs(f.pan_temp_c - self._state.last_llm_temp) >= 10:
                return True
            if f.pan_temp_c >= 220:  # always escalate when close to smoke point
                return True
        return False

    async def _think(self) -> None:
        self._state.last_llm_call = datetime.now()
        if self._state.last_frame is not None and self._state.last_frame.pan_temp_c is not None:
            self._state.last_llm_temp = self._state.last_frame.pan_temp_c

        user_text = self._compose_observation()
        user_msg = self._build_user_message(user_text)
        self._history.append({"role": "user", "content": user_msg})
        log_preview = user_text if isinstance(user_msg, str) else f"{user_text} [+image]"
        console.log(f"[claude-agent] -> LLM: {log_preview}")

        for _round in range(4):  # cap tool-use rounds
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *self._history],
                tools=self._tools,
                tool_choice="auto",
                temperature=0.2,
            )
            msg = resp.choices[0].message
            assistant_entry: dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self._history.append(assistant_entry)

            if msg.content:
                console.log(f"[claude-agent] say: {msg.content}")

            if not msg.tool_calls:
                break

            for tc in msg.tool_calls:
                result = await self._invoke_tool(tc.function.name, tc.function.arguments)
                self._history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        self._trim_history()

    def _build_user_message(self, text: str):
        """Return either a plain string or a multimodal list of content parts.

        When the latest frame carries an image_b64, attach it as an image_url part so the
        VLM can actually *see* the pan, not just read our text description.
        """
        img = self._state.last_frame.image_b64 if self._state.last_frame else None
        if not img:
            return text
        return [
            {"type": "text", "text": text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"},
            },
        ]

    def _compose_observation(self) -> str:
        parts: list[str] = []
        if self._state.last_utterance:
            parts.append(f'User said: "{self._state.last_utterance.text}"')
        if self._state.last_frame:
            f = self._state.last_frame
            bits: list[str] = []
            if f.pan_temp_c is not None:
                bits.append(f"pan {f.pan_temp_c:.0f}C")
            if f.contents:
                bits.append(f"'{f.contents}'")
            if f.image_b64 and not bits:
                bits.append("camera view attached")
            if bits:
                parts.append("Cooktop: " + ", ".join(bits) + ".")
        if self._state.recent_audio:
            kinds = ", ".join(a.kind for a in self._state.recent_audio[-3:])
            parts.append(f"Recent sounds: {kinds}.")
        ps = self._state.plan_state
        if ps and ps.plan and 0 <= ps.step_index < len(ps.plan.steps):
            step = ps.plan.steps[ps.step_index]
            tgt = f"{step.target_pan_c:.0f}C" if step.target_pan_c else "n/a"
            parts.append(
                f"Active plan '{ps.plan.dish}', step {ps.step_index + 1}/"
                f"{len(ps.plan.steps)}: {step.description} (target {tgt})."
            )
        if self._state.recent_alerts:
            a = self._state.recent_alerts[-1]
            parts.append(f"!! SAFETY ALERT [{a.kind}]: {a.detail}")
            # Consume after read to avoid re-raising the same alert every call.
            self._state.recent_alerts = []
        return " ".join(parts) if parts else "No new observations."

    async def _invoke_tool(self, name: str, args_json: str) -> str:
        s = self._skill_map.get(name)
        if s is None:
            return f"error: unknown skill {name}"
        try:
            args = json.loads(args_json) if args_json else {}
        except json.JSONDecodeError:
            return "error: bad json arguments"
        console.log(f"[claude-agent] call {name}({args})")
        try:
            result = await s.fn(**args)
            return str(result)
        except Exception as e:  # noqa: BLE001
            return f"error: {e}"

    def _trim_history(self) -> None:
        if len(self._history) > self.max_history_turns * 2:
            self._history = self._history[-self.max_history_turns * 2 :]
