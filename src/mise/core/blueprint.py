from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console

from mise.core.module import Module
from mise.core.stream import Stream, _StreamHandle

console = Console()


class Blueprint:
    """Composes modules by type-matching their Out[T] / In[T] handles.

    Rule: for each Out[T] on some module, every In[T] of the same payload type on any other
    module subscribes to it. If a type has multiple producers or consumers, all connect.
    """

    def __init__(self, modules: list[Module]) -> None:
        self.modules = modules
        self._streams: dict[type, Stream[Any]] = {}
        self._wire()

    def _wire(self) -> None:
        for m in self.modules:
            for attr, handle in list(vars(type(m)).items()):
                if not isinstance(handle, _StreamHandle) or handle.direction != "out":
                    continue
                t = handle.payload_type
                stream = self._streams.setdefault(t, Stream(t.__name__, t))
                setattr(m, attr, stream)

        for m in self.modules:
            for attr, handle in list(vars(type(m)).items()):
                if not isinstance(handle, _StreamHandle) or handle.direction != "in":
                    continue
                t = handle.payload_type
                stream = self._streams.get(t)
                if stream is None:
                    stream = Stream(t.__name__, t)
                    self._streams[t] = stream
                setattr(m, attr, stream.subscribe())

    async def run(self) -> None:
        console.log(f"[blueprint] starting {len(self.modules)} modules")
        for m in self.modules:
            console.log(f"  - {m}")
        await asyncio.gather(*(m.run() for m in self.modules))


def autoconnect(*modules: Module) -> Blueprint:
    return Blueprint(list(modules))
