from __future__ import annotations

from typing import Literal

from mise.agent.claude_agent import ClaudeAgent
from mise.agent.stub_agent import StubAgent
from mise.core.blueprint import Blueprint, autoconnect
from mise.core.module import Module
from mise.perception.sim_stove import SimStove
from mise.perception.stdin_voice import StdinVoice
from mise.skills.burner import BurnerModule
from mise.skills.cook_plan import CookPlanModule
from mise.skills.notify import NotifyModule
from mise.skills.sous_chef import SousChefModule

AgentKind = Literal["stub", "claude"]


def sim_blueprint(
    initial_burner_percent: int = 70,
    agent: AgentKind = "stub",
    model: str = "anthropic/claude-sonnet-4.6",
    sous_chef_model: str = "anthropic/claude-opus-4.7",
    audio: bool = False,
    whisper_model: str = "small.en",
    images: bool = False,
) -> Blueprint:
    audio_gate = None
    voice: Module
    if audio:
        from mise.audio.gate import AudioGate  # noqa: PLC0415
        from mise.perception.mic_voice import MicVoice  # noqa: PLC0415

        audio_gate = AudioGate()
        voice = MicVoice(audio_gate=audio_gate, model_size=whisper_model)
    else:
        voice = StdinVoice()

    stove = SimStove(tick_seconds=1.0, render_images=images)
    burner = BurnerModule()
    burner.percent = initial_burner_percent
    burner.on = initial_burner_percent > 0
    notify = NotifyModule(audio_gate=audio_gate)
    cook_plan = CookPlanModule()
    sous_chef = SousChefModule(model=sous_chef_model) if agent == "claude" else None

    agent_mod: Module
    if agent == "claude":
        skill_modules: list[Module] = [burner, notify, cook_plan]
        if sous_chef is not None:
            skill_modules.append(sous_chef)
        agent_mod = ClaudeAgent(skill_modules=skill_modules, model=model)
    else:
        agent_mod = StubAgent(burner=burner, notify=notify)

    modules: list[Module] = [stove, burner, notify, voice, cook_plan, agent_mod]
    if sous_chef is not None:
        modules.append(sous_chef)
    return autoconnect(*modules)
