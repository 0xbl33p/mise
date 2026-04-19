from __future__ import annotations

from mise.agent.claude_agent import ClaudeAgent
from mise.core.blueprint import Blueprint, autoconnect
from mise.core.module import Module
from mise.memory.temporal import MemoryModule
from mise.server.bridge import BrowserBridge
from mise.skills.burner import BurnerModule
from mise.skills.cook_plan import CookPlanModule
from mise.skills.notify import NotifyModule
from mise.skills.shelly_burner import ShellyBurner
from mise.skills.sous_chef import SousChefModule


def browser_blueprint(
    model: str = "anthropic/claude-sonnet-4.6",
    sous_chef_model: str = "anthropic/claude-opus-4.7",
    plug_ip: str | None = None,
) -> tuple[Blueprint, BrowserBridge]:
    """Wire the module graph for browser mode. Returns (blueprint, bridge) so the server
    can hook the WebSocket into the bridge.

    When plug_ip is provided, a real ShellyBurner drives the cooktop. Otherwise the sim
    BurnerModule is used (no physical side effects, prints only)."""
    bridge = BrowserBridge()
    burner: Module
    if plug_ip:
        burner = ShellyBurner(host=plug_ip)
    else:
        burner = BurnerModule()
    cook_plan = CookPlanModule()
    sous_chef = SousChefModule(model=sous_chef_model)
    memory = MemoryModule()
    notify = NotifyModule(
        audio_gate=None,  # TTS happens in the browser
        on_speak=bridge.on_agent_speak,
        on_text=bridge.on_agent_text,
    )
    agent = ClaudeAgent(
        skill_modules=[burner, notify, cook_plan, sous_chef, memory],
        model=model,
    )

    modules: list[Module] = [bridge, burner, notify, cook_plan, sous_chef, memory, agent]
    return autoconnect(*modules), bridge
