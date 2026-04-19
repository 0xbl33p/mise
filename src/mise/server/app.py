from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rich.console import Console

from mise.server.bridge import BrowserBridge

console = Console()
STATIC_DIR = Path(__file__).parent / "static"


def build_app(bridge: BrowserBridge, blueprint_run_coro) -> FastAPI:  # noqa: ANN001
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        task = asyncio.create_task(blueprint_run_coro())
        console.log("[server] blueprint running")
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(lifespan=lifespan, title="Mise")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @app.websocket("/ws")
    async def ws(ws: WebSocket) -> None:
        await ws.accept()
        bridge.set_socket(ws)
        console.log("[server] websocket connected")
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                kind = msg.get("type")
                if kind == "frame":
                    image_b64 = msg.get("image_b64", "")
                    if image_b64:
                        await bridge.on_browser_frame(image_b64)
                elif kind == "utterance":
                    await bridge.on_browser_utterance(msg.get("text", ""))
                elif kind == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
        except WebSocketDisconnect:
            console.log("[server] websocket disconnected")
        finally:
            bridge.clear_socket()

    return app
