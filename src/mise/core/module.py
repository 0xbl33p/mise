from __future__ import annotations

import asyncio
from typing import Any


class Module:
    """Base class for all Mise modules. Subclasses declare In[T] / Out[T] stream handles as
    class attributes and implement an async `run()` coroutine.

    The Blueprint replaces each handle with a real Stream (for outputs) or a Queue (for inputs)
    before `run()` is awaited.
    """

    name: str = ""

    def __init__(self, **kwargs: Any) -> None:
        self._kwargs = kwargs
        if not self.name:
            self.name = self.__class__.__name__

    async def run(self) -> None:  # pragma: no cover - override in subclass
        raise NotImplementedError

    async def emit(self, stream_attr: str, msg: Any) -> None:
        stream = getattr(self, stream_attr)
        await stream.publish(msg)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
