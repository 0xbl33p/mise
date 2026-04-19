from __future__ import annotations

import asyncio
import json
from datetime import datetime

from rich.console import Console

from mise.core.module import Module
from mise.core.skill import skill
from mise.core.stream import Out
from mise.messages import CookPlan, CookPlanState, CookStep

console = Console()


class CookPlanModule(Module):
    """Holds the active cooking plan and emits a CookPlanState stream whenever it changes.

    The reactive agent subscribes to that stream (in Phase 3) to bias heat decisions toward
    the step's target temperature.
    """

    state_out = Out(CookPlanState)

    def __init__(self) -> None:
        super().__init__()
        self._plan: CookPlan | None = None
        self._step_index: int = 0
        self._started_step_at: datetime | None = None

    async def run(self) -> None:
        while True:
            await asyncio.sleep(3600)

    async def _publish(self) -> None:
        await self.state_out.publish(
            CookPlanState(
                plan=self._plan,
                step_index=self._step_index,
                started_step_at=self._started_step_at,
            )
        )

    @skill
    async def start_cook_plan(self, plan_json: str) -> str:
        """Install an active cooking plan. Pass the JSON returned by ask_sous_chef."""
        try:
            parsed = json.loads(plan_json)
            steps = [CookStep(**s) for s in parsed["steps"]]
            self._plan = CookPlan(dish=parsed["dish"], steps=steps)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            return f"error: bad plan_json ({e})"
        self._step_index = 0
        self._started_step_at = datetime.now()
        await self._publish()
        first = self._plan.steps[0]
        return (
            f"started '{self._plan.dish}' ({len(self._plan.steps)} steps). "
            f"step 1/{len(self._plan.steps)}: {first.description}"
        )

    @skill
    async def current_step(self) -> str:
        """Return the current step the user is on, or 'no plan' if none is active."""
        if not self._plan:
            return "no plan"
        if self._step_index < 0 or self._step_index >= len(self._plan.steps):
            return f"'{self._plan.dish}' is complete"
        s = self._plan.steps[self._step_index]
        tgt = f"{s.target_pan_c:.0f}C" if s.target_pan_c else "n/a"
        return (
            f"step {self._step_index + 1}/{len(self._plan.steps)} of '{self._plan.dish}': "
            f"{s.description} (target pan {tgt}"
            + (f", ~{s.duration_s:.0f}s" if s.duration_s else "")
            + ")"
        )

    @skill
    async def advance_step(self) -> str:
        """Mark the current step done and move to the next one. Returns the new current step."""
        if not self._plan:
            return "error: no plan active"
        self._step_index += 1
        self._started_step_at = datetime.now()
        if self._step_index >= len(self._plan.steps):
            self._step_index = -1
            await self._publish()
            return f"'{self._plan.dish}' is complete"
        await self._publish()
        return await self.current_step()

    @skill
    async def abort_plan(self) -> str:
        """Abort the current plan. Use when the user decides to stop cooking."""
        if not self._plan:
            return "no plan to abort"
        name = self._plan.dish
        self._plan = None
        self._step_index = 0
        self._started_step_at = None
        await self._publish()
        return f"aborted '{name}'"
