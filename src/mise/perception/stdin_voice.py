from __future__ import annotations

import asyncio
import sys

from mise.core.module import Module
from mise.core.stream import Out
from mise.messages import UserUtterance


class StdinVoice(Module):
    """Placeholder for the real mic-in: read lines from stdin and publish as UserUtterance.

    Real mode swaps this for a Whisper-small-powered mic listener publishing the same type.
    """

    utter = Out(UserUtterance)

    async def run(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            line = (line or "").strip()
            if not line:
                await asyncio.sleep(0.5)
                continue
            await self.utter.publish(UserUtterance(text=line))
