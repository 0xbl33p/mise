from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from mise.core.module import Module
from mise.core.skill import skill
from mise.core.stream import In
from mise.messages import CookPlanState, SafetyAlert, UserUtterance

console = Console()


class MemoryModule(Module):
    """JSON-lines temporal memory.

    Subscribes to user utterances, plan transitions, and safety alerts and appends each
    to a persistent event log. Exposes one skill — `recall(query)` — that does text-match
    retrieval so the agent can answer "have I made this before?" style questions.

    Intentionally simple: no embeddings, no torch, no vector DB. Upgrade to semantic
    search later by swapping _score() for an embedding lookup without touching callers.
    """

    utter_in = In(UserUtterance)
    plan_in = In(CookPlanState)
    alert_in = In(SafetyAlert)

    def __init__(self, path: str = ".mise_state/memory.jsonl") -> None:
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._session = datetime.now().isoformat(timespec="seconds")
        self._lock = asyncio.Lock()

    async def run(self) -> None:
        # Write a session-start marker so users can tell sessions apart.
        self._append({"kind": "session_start", "text": f"new session @ {self._session}"})
        await asyncio.gather(
            self._watch_utterances(),
            self._watch_plans(),
            self._watch_alerts(),
        )

    # ---- ingestors -----------------------------------------------------------

    async def _watch_utterances(self) -> None:
        while True:
            u: UserUtterance = await self.utter_in.get()
            self._append({"kind": "user", "text": u.text})

    async def _watch_plans(self) -> None:
        last_dish: str | None = None
        last_step: int | None = None
        while True:
            p: CookPlanState = await self.plan_in.get()
            if p.plan is None:
                continue
            if p.step_index < 0:
                self._append(
                    {
                        "kind": "plan_complete",
                        "text": f"finished cooking {p.plan.dish}",
                        "dish": p.plan.dish,
                    }
                )
                last_dish = None
                last_step = None
                continue
            # Only log on changes (not every republish).
            if p.plan.dish != last_dish:
                self._append(
                    {
                        "kind": "plan_start",
                        "text": f"started cooking {p.plan.dish} ({len(p.plan.steps)} steps)",
                        "dish": p.plan.dish,
                    }
                )
                last_dish = p.plan.dish
                last_step = None
            if p.step_index != last_step and 0 <= p.step_index < len(p.plan.steps):
                step = p.plan.steps[p.step_index]
                self._append(
                    {
                        "kind": "plan_step",
                        "text": (
                            f"cooking {p.plan.dish}, step {p.step_index + 1}: "
                            f"{step.description}"
                        ),
                        "dish": p.plan.dish,
                        "step_index": p.step_index,
                        "target_pan_c": step.target_pan_c,
                    }
                )
                last_step = p.step_index

    async def _watch_alerts(self) -> None:
        while True:
            a: SafetyAlert = await self.alert_in.get()
            self._append({"kind": f"alert_{a.kind}", "text": a.detail})

    # ---- storage + retrieval -------------------------------------------------

    def _append(self, record: dict[str, Any]) -> None:
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "session": self._session,
            **record,
        }
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            console.log(f"[memory] write failed: {e}")

    def _all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def _score(self, query: str, record: dict[str, Any]) -> int:
        text = (record.get("text") or "").lower()
        dish = (record.get("dish") or "").lower()
        q_words = {w for w in query.lower().split() if len(w) > 2}
        if not q_words:
            return 0
        return sum(1 for w in q_words if w in text or w in dish)

    @skill
    async def recall(self, query: str, n: int = 5) -> str:
        """Search past cooking sessions for memories matching a query. Use when the user \
asks about their history ("have I made this before?", "how did it go last time?", \
"did I burn anything yesterday?")."""
        records = self._all()
        # Exclude the very latest user utterance so the agent doesn't just echo the
        # question back at itself.
        scored = [(self._score(query, r), r) for r in records]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda x: (x[0], x[1].get("ts", "")), reverse=True)
        if not scored:
            return "no relevant memories"
        lines = []
        for _score, r in scored[:n]:
            lines.append(f"- [{r.get('ts', '?')}] {r.get('text', '')}")
        return "\n".join(lines)
