from __future__ import annotations

import asyncio
import json
import os

from openai import AsyncOpenAI
from rich.console import Console

from mise.core.module import Module
from mise.core.skill import skill

console = Console()

SOUS_CHEF_SYSTEM = """You are Mise's sous-chef — a calm, experienced home cook. You are \
called by the reactive agent when the user needs recipe guidance.

Given available ingredients and a question, design ONE dish that is genuinely achievable \
with what's on hand. Return valid JSON matching this shape exactly:

{
  "dish": "short name",
  "steps": [
    {"description": "one sentence", "target_pan_c": 180, "duration_s": 120, "notes": ""},
    ...
  ]
}

- 3 to 8 steps. Each step should be one clear cooking action.
- target_pan_c: approximate pan temperature the user should aim for (60-250).
- duration_s: how long the step should take. null if it runs "until X happens".
- notes: optional one-line cooking tip (e.g. "don't flip early — wait for the sear").

Output ONLY the JSON object. No prose, no markdown fencing."""


class SousChefModule(Module):
    """Owns its own Opus 4.7 client. One skill: ask_sous_chef. Synchronous-ish from the
    caller's perspective — returns the plan as a JSON string the reactive agent can pass
    to CookPlanModule.start_cook_plan."""

    async def run(self) -> None:
        while True:
            await asyncio.sleep(3600)

    def __init__(self, model: str = "anthropic/claude-opus-4.7") -> None:
        super().__init__()
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1", api_key=api_key
        )
        self.model = model
        self.last_plan_json: str | None = None

    @skill
    async def ask_sous_chef(self, question: str, available_ingredients: str = "") -> str:
        """Ask the sous-chef to design a cooking plan. Use when the user needs recipe \
guidance ("what can I make with X?", "walk me through making Y"). Returns a JSON plan \
that you can pass to start_cook_plan to activate it.

        Args:
            question: what the user asked in natural language.
            available_ingredients: comma-separated list of what they have, if known.
        """
        user_content = question
        if available_ingredients:
            user_content += f"\n\nAvailable ingredients: {available_ingredients}"

        console.log(f"[sous-chef] -> Opus: {question[:80]}")
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SOUS_CHEF_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.4,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Strip accidental fences in case the model defies the prompt
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            return f"error: sous-chef returned invalid JSON ({e}): {raw[:200]}"

        self.last_plan_json = json.dumps(parsed)
        console.log(f"[sous-chef] plan: {parsed.get('dish', '?')} ({len(parsed.get('steps', []))} steps)")
        return self.last_plan_json
