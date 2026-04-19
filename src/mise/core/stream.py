from __future__ import annotations

import asyncio
from typing import Generic, TypeVar

T = TypeVar("T")


class Stream(Generic[T]):
    """A fan-out pub/sub stream. Writers publish once, every subscriber sees the message."""

    def __init__(self, name: str, payload_type: type[T]) -> None:
        self.name = name
        self.payload_type = payload_type
        self._subscribers: list[asyncio.Queue[T]] = []

    def subscribe(self, maxsize: int = 64) -> asyncio.Queue[T]:
        q: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(q)
        return q

    async def publish(self, msg: T) -> None:
        for q in self._subscribers:
            if q.full():
                q.get_nowait()
            await q.put(msg)

    def __repr__(self) -> str:
        return f"Stream({self.name}: {self.payload_type.__name__})"


class _StreamHandle(Generic[T]):
    """Class-level marker used on Module subclasses to declare an input or output stream.

    The Blueprint reads these markers and substitutes real Stream / Queue objects at wire time.
    """

    def __init__(self, payload_type: type[T], *, direction: str) -> None:
        self.payload_type = payload_type
        self.direction = direction  # "in" | "out"


def Out(payload_type: type[T]) -> _StreamHandle[T]:  # noqa: N802
    return _StreamHandle(payload_type, direction="out")


def In(payload_type: type[T]) -> _StreamHandle[T]:  # noqa: N802
    return _StreamHandle(payload_type, direction="in")
