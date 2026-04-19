<p align="center">
  <img src="assets/logo.png" alt="Mise" width="200">
</p>

<h1 align="center">mise</h1>

<p align="center">
  An agentic kitchen copilot. Watches your stove through any camera, remembers what you cook,<br/>
  and cuts the power when oil smokes.
</p>

<p align="center">
  Runs on your laptop. Uses your own OpenRouter key. Your kitchen, your data.
</p>

---

## What it does

- **Sees your stove** — phone or laptop camera streams frames to Claude's vision model. Distinguishes steam, smoke, oil shimmer, and browning.
- **Plans with you** — say *"I have chicken, rice, soy sauce — walk me through it"*. Opus designs a step-by-step cook plan; Sonnet coaches you through it.
- **Keeps you safe** — if the pan is smoking or you walked away while the burner is hot, Mise cuts power via a smart plug and texts you.
- **Remembers** — every session is logged. *"Have I made this before?"* works.
- **Talks** — hold-to-talk mic on your phone, TTS replies through the phone speaker. No app install; it's a browser.

## Stack

- Python 3.11+, asyncio, Pydantic
- Claude Sonnet 4.6 (reactive loop) + Opus 4.7 (sous-chef planner) via OpenRouter
- FastAPI backend, static Next.js frontend
- `faster-whisper` + `pyttsx3` for local audio (dev mode)
- Browser Web Speech API (serve mode)
- Shelly Plus Plug US for real-world actuation

## Quick start

```bash
git clone <this repo>
cd mise
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate on mac/linux
pip install -e .
```

Set your OpenRouter key:

```bash
echo "OPENROUTER_API_KEY=sk-or-..." > .env
```

Grab one at [openrouter.ai/keys](https://openrouter.ai/keys).

### Run the simulator (no hardware)

```bash
mise run sim --agent claude --images --duration 60
```

Synthetic stove, synthetic pan images, full agent loop end-to-end.

### Run the browser UI

```bash
mise serve --https --host 0.0.0.0
```

Open `https://<your-lan-ip>:8080` on your phone. Accept the self-signed cert warning once. Prop the phone on the counter — the phone's camera, mic, and speaker become the perception and actuation surface.

With a real smart plug:

```bash
mise serve --https --host 0.0.0.0 --plug-ip 192.168.1.XX
```

## Hardware

One thing, optional:

- **Shelly Plus Plug US** ($22.99) — smart plug with a local HTTP REST API, live power monitoring, 15A/1800W. No cloud round-trip. [Home Depot](https://www.homedepot.com/p/Shelly-Plus-Plug-US-WiFi-and-Bluetooth-Operated-Smart-Plug-With-Power-Measurement-Home-Automation-Remote-Control-Shelly-Plus-Plug-US-1/327539186) / [Shelly direct](https://us.shelly.com/products/shelly-plus-plug-us) / [Amazon](https://www.amazon.com/Shelly-Measurement-Automation-Compatible-Appliances/dp/B0D6GNQMDG).

Plug any electric appliance into it — a kettle works for the first demo. Mise doesn't need a specific cooktop; it just needs something it can cut power to.

## Architecture

A dimos-style module graph: typed async streams carry perception into the agent, the agent routes tool calls to skills, skills actuate the real world.

```
┌────────────────┐   StoveFrame, AudioEvent, UserUtterance
│ perception     │ ───────────────────────────────────►
│  - SimStove    │
│  - MicVoice    │
│  - BrowserBridge
└────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  ClaudeAgent     │ Sonnet 4.6, multimodal
                    │  (rate-limited)  │
                    └──────────────────┘
                             │ tool calls
                             ▼
┌──────────────────────────────────────────────┐
│ skills (each a Module, exposes @skill methods)│
│  - BurnerModule / ShellyBurner               │
│  - NotifyModule    (speak, text_user)        │
│  - CookPlanModule  (start/advance/abort)     │
│  - SousChefModule  (calls Opus 4.7)          │
│  - MemoryModule    (JSON-lines + recall)     │
└──────────────────────────────────────────────┘
```

Every module is isolated; streams are typed; skills are discoverable. Swap `SimStove` for a real webcam module, swap `BurnerModule` for `ShellyBurner`, and nothing else changes.

## Website

A landing page lives in `website/` (Next.js + Tailwind + shadcn/ui).

```bash
cd website
npm install
npm run dev       # http://localhost:3000
npm run build     # static output in out/
```

## Repository layout

```
src/mise/
├── core/           Stream[T], Module, @skill decorator, Blueprint.autoconnect()
├── messages.py     Pydantic messages (StoveFrame, AudioEvent, CookPlan, SafetyAlert, ...)
├── agent/          ClaudeAgent (LLM) + StubAgent (rule-based, offline)
├── skills/         BurnerModule, ShellyBurner, NotifyModule, CookPlanModule, SousChefModule
├── memory/         Persistent session log with a recall skill
├── perception/     SimStove + PIL renderer, StdinVoice, MicVoice (Whisper), pan_render
├── audio/          AudioGate — TTS/mic feedback-loop guard
├── server/         FastAPI app, BrowserBridge, self-signed HTTPS
├── blueprints/     sim_blueprint, browser_blueprint
└── cli.py          `mise run sim` | `mise serve`
website/            Next.js landing page
```

## License

MIT.
