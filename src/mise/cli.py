from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from mise.blueprints.sim import sim_blueprint

# Windows consoles default to cp1252 which can't render LLM-emitted emoji.
# Reconfigure stdout/stderr early so LLM responses don't crash the process.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

app = typer.Typer(help="Mise — agentic kitchen copilot")
run_app = typer.Typer(help="Run a blueprint")
app.add_typer(run_app, name="run")

console = Console()


def _load_env() -> None:
    repo_env = Path(__file__).resolve().parents[2] / ".env"
    if repo_env.exists():
        load_dotenv(repo_env, override=False)


@run_app.command("sim")
def run_sim(
    burner: int = typer.Option(70, help="Initial burner percent 0-100"),
    duration: float = typer.Option(60.0, help="Seconds to run (0 = forever)"),
    agent: str = typer.Option("stub", help="Agent backend: stub | claude"),
    model: str = typer.Option(
        "anthropic/claude-sonnet-4.6", help="OpenRouter model id (claude agent only)"
    ),
    sous_chef_model: str = typer.Option(
        "anthropic/claude-opus-4.7", help="OpenRouter model id for the sous-chef (Opus)"
    ),
    audio: bool = typer.Option(
        False, help="Enable always-on mic (STT via faster-whisper) + TTS (pyttsx3)"
    ),
    whisper_model: str = typer.Option(
        "small.en", help="faster-whisper model size (tiny.en | base.en | small.en | medium.en)"
    ),
    images: bool = typer.Option(
        False, help="Render synthetic pan images and send them to the VLM (claude agent only)"
    ),
) -> None:
    """Run the fully-simulated kitchen — no hardware required.

    Without --audio: type lines into stdin to send utterances.
    With --audio: speak naturally; VAD chunks your speech and Whisper transcribes it.
    """
    _load_env()
    bp = sim_blueprint(
        initial_burner_percent=burner,
        agent=agent,  # type: ignore[arg-type]
        model=model,
        sous_chef_model=sous_chef_model,
        audio=audio,
        whisper_model=whisper_model,
        images=images,
    )

    async def _main() -> None:
        task = asyncio.create_task(bp.run())
        if duration > 0:
            await asyncio.sleep(duration)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        else:
            await task

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        console.log("[cli] interrupted")


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind. Use 0.0.0.0 for LAN access."),
    port: int = typer.Option(8080, help="Port to bind."),
    model: str = typer.Option(
        "anthropic/claude-sonnet-4.6", help="OpenRouter model id for the reactive agent"
    ),
    sous_chef_model: str = typer.Option(
        "anthropic/claude-opus-4.7", help="OpenRouter model id for the sous-chef"
    ),
    plug_ip: str = typer.Option(
        "",
        help="Shelly Plus Plug US IP address (e.g. 192.168.1.42). Leave empty for sim.",
    ),
    https: bool = typer.Option(
        False,
        "--https",
        help="Serve over HTTPS with an auto-generated self-signed cert. "
        "Required for phone camera/mic access.",
    ),
) -> None:
    """Start the browser UI server. Open http://HOST:PORT on any device on your network."""
    _load_env()
    import uvicorn  # noqa: PLC0415

    from mise.blueprints.browser import browser_blueprint  # noqa: PLC0415
    from mise.server.app import build_app  # noqa: PLC0415

    bp, bridge = browser_blueprint(
        model=model,
        sous_chef_model=sous_chef_model,
        plug_ip=plug_ip or None,
    )
    fastapi_app = build_app(bridge, bp.run)

    ssl_kwargs: dict = {}
    scheme = "http"
    if https:
        from mise.server.https import ensure_self_signed_cert  # noqa: PLC0415

        cert_path, key_path = ensure_self_signed_cert(Path(".mise_state"))
        ssl_kwargs = {"ssl_certfile": str(cert_path), "ssl_keyfile": str(key_path)}
        scheme = "https"
        console.log(f"[serve] HTTPS enabled (cert cached at {cert_path})")
        console.log(
            "[serve] phone will warn 'not secure' — tap Advanced -> Proceed. "
            "One-time per device."
        )

    url = f"{scheme}://{host}:{port}"
    console.log(f"[serve] open {url} on this machine — or {scheme}://<lan-ip>:{port} from another device")
    if host == "127.0.0.1":
        console.log("[serve] NOTE: --host 127.0.0.1 means localhost only. For phone access use --host 0.0.0.0")
    uvicorn.run(fastapi_app, host=host, port=port, log_level="warning", **ssl_kwargs)


if __name__ == "__main__":
    app()
