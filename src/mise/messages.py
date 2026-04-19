from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now()


class StoveFrame(BaseModel):
    """A snapshot of the cooktop.

    - In sim mode, pan_temp_c and contents are synthetic.
    - In browser / real-webcam mode, pan_temp_c may be None (no thermal sensor) and the VLM
      reasons off image_b64 alone.
    """

    ts: datetime = Field(default_factory=_now)
    pan_temp_c: float | None = None
    contents: str = ""  # short natural-language description of what the VLM "sees"
    image_b64: str | None = None  # real mode fills this in for VLM calls


class AudioEvent(BaseModel):
    ts: datetime = Field(default_factory=_now)
    kind: Literal["sizzle", "boil", "smoke_alarm", "silence", "oil_crackle"]
    confidence: float = 1.0


class PlugTelemetry(BaseModel):
    ts: datetime = Field(default_factory=_now)
    watts: float
    on: bool


class UserUtterance(BaseModel):
    ts: datetime = Field(default_factory=_now)
    text: str


class AgentAction(BaseModel):
    """Record of a skill call the agent decided to make. Emitted for logging / UI."""

    ts: datetime = Field(default_factory=_now)
    skill: str
    args: dict[str, object] = Field(default_factory=dict)
    reason: str = ""


class CookStep(BaseModel):
    """One step of an active CookPlan."""

    description: str
    target_pan_c: float | None = None  # ideal pan temp during this step
    duration_s: float | None = None  # suggested duration, None = until user advances
    notes: str = ""


class CookPlan(BaseModel):
    dish: str
    steps: list[CookStep]


class CookPlanState(BaseModel):
    """Snapshot of the current cook plan + index. Emitted whenever the plan advances."""

    ts: datetime = Field(default_factory=_now)
    plan: CookPlan | None = None
    step_index: int = 0  # -1 when finished
    started_step_at: datetime | None = None


class SafetyAlert(BaseModel):
    """Urgent cross-module signal. The agent treats these as priority LLM calls."""

    ts: datetime = Field(default_factory=_now)
    kind: Literal["power_after_kill", "plug_unreachable", "hardware_error"]
    detail: str
