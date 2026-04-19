from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Skill:
    """An LLM-callable method on a Module. Schema is derived from annotations + docstring."""

    name: str
    description: str
    fn: Callable[..., Any]
    parameters: dict[str, Any]  # JSON-schema-ish: {name: {type, required, default}}


def skill(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as LLM-invocable. The docstring becomes the description sent to the model."""
    fn.__mise_skill__ = True  # type: ignore[attr-defined]
    return fn


def _annotation_to_schema(ann: type) -> dict[str, Any]:
    mapping: dict[type, str] = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }
    return {"type": mapping.get(ann, "string")}


def skill_to_openai_tool(s: Skill) -> dict[str, Any]:
    """Convert a Skill to the OpenAI / OpenRouter tool-use JSON schema."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for p_name, p_schema in s.parameters.items():
        properties[p_name] = {"type": p_schema["type"]}
        if p_schema.get("required"):
            required.append(p_name)
    return {
        "type": "function",
        "function": {
            "name": s.name,
            "description": s.description or s.name,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def get_skills(module: object) -> list[Skill]:
    skills: list[Skill] = []
    for name in dir(module):
        fn = getattr(module, name, None)
        if not callable(fn) or not getattr(fn, "__mise_skill__", False):
            continue
        sig = inspect.signature(fn)
        params: dict[str, Any] = {}
        for p_name, p in sig.parameters.items():
            if p_name == "self":
                continue
            schema = _annotation_to_schema(p.annotation if p.annotation is not inspect._empty else str)
            schema["required"] = p.default is inspect._empty
            if p.default is not inspect._empty:
                schema["default"] = p.default
            params[p_name] = schema
        skills.append(
            Skill(
                name=name,
                description=(fn.__doc__ or "").strip(),
                fn=fn,
                parameters=params,
            )
        )
    return skills
