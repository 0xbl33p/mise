import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Brain,
  Camera,
  Eye,
  Flame,
  Github,
  History,
  ShieldAlert,
  Wifi,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const REPO = "https://github.com/0xbl33p/mise";
const GITHUB_USER = "https://github.com/0xbl33p";

export default function Home() {
  return (
    <main className="flex flex-col">
      <Nav />
      <Hero />
      <Features />
      <HowItWorks />
      <Hardware />
      <QuickStart />
      <Footer />
    </main>
  );
}

function Nav() {
  return (
    <nav className="sticky top-0 z-40 border-b border-border/60 backdrop-blur-md bg-background/70">
      <div className="container flex h-14 items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/mise-logo.png"
            alt="Mise"
            width={28}
            height={28}
            className="drop-shadow-[0_0_12px_rgba(74,222,128,0.6)]"
          />
          <span className="font-semibold tracking-tight">mise</span>
        </Link>
        <div className="flex items-center gap-2">
          <Link href="#hardware" className="hidden sm:block text-sm text-muted-foreground hover:text-foreground transition-colors">
            hardware
          </Link>
          <Link href="#quickstart" className="hidden sm:block text-sm text-muted-foreground hover:text-foreground transition-colors">
            quick start
          </Link>
          <Link href={REPO} target="_blank" rel="noreferrer">
            <Button variant="outline" size="sm" className="gap-2">
              <Github className="h-4 w-4" />
              github
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section className="container flex flex-col items-center text-center pt-16 pb-24 sm:pt-24 sm:pb-32">
      <div className="relative flex items-center justify-center mb-2">
        <div className="absolute inset-0 bg-mint/20 blur-3xl rounded-full scale-150" aria-hidden />
        <Image
          src="/mise-logo.png"
          alt="Mise logo"
          width={176}
          height={176}
          priority
          className="relative drop-shadow-[0_0_40px_rgba(74,222,128,0.5)]"
        />
      </div>

      <h1
        className="text-7xl sm:text-8xl md:text-9xl font-black tracking-tight leading-[1.3] pb-6 mb-4 overflow-visible bg-gradient-to-b from-white via-mint to-mint/70 bg-clip-text text-transparent"
        style={{ textShadow: "0 0 40px rgba(74, 222, 128, 0.4)" }}
      >
        mise
      </h1>

      <p className="text-3xl sm:text-5xl font-bold tracking-tight text-balance max-w-3xl">
        The agentic kitchen copilot
      </p>
      <p className="mt-5 text-lg sm:text-xl text-muted-foreground max-w-2xl text-balance">
        Mise watches your stove through any camera, remembers what you cook, and cuts the
        power if you walk away. Runs on your laptop. Your kitchen, your data.
      </p>

      <div className="mt-8 flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
        <Link href={REPO} target="_blank" rel="noreferrer" className="w-full sm:w-auto">
          <Button size="lg" className="w-full gap-2">
            <Github className="h-4 w-4" />
            clone the repo
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
        <Link href="#hardware" className="w-full sm:w-auto">
          <Button size="lg" variant="outline" className="w-full">
            what you'll need
          </Button>
        </Link>
      </div>

      <div className="mt-10 flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">Claude Sonnet 4.6 + Opus 4.7</Badge>
        <Badge variant="outline">FastAPI + Next.js</Badge>
        <Badge variant="outline">runs offline</Badge>
      </div>
    </section>
  );
}

function Features() {
  const items = [
    {
      icon: Eye,
      title: "Sees your stove",
      body:
        "Your phone or laptop camera streams frames to a vision-language model. Mise knows the difference between steam, smoke, and oil shimmer.",
    },
    {
      icon: Brain,
      title: "Plans with you",
      body:
        "Ask \"I have chicken, rice, soy sauce — walk me through it.\" Opus 4.7 designs a step-by-step plan; Sonnet 4.6 coaches you through it in real time.",
    },
    {
      icon: ShieldAlert,
      title: "Keeps you safe",
      body:
        "If the pan is smoking and you left the kitchen, Mise cuts power to the burner via a smart plug — and texts you while it's doing it.",
    },
    {
      icon: History,
      title: "Remembers",
      body:
        "Every cook session is logged. Ask \"have I made this before?\" or \"how did it go last time?\" and Mise answers from actual history.",
    },
    {
      icon: Camera,
      title: "Works on your phone",
      body:
        "Prop your phone on the counter, open the site. Uses the phone's camera, mic, and speaker. No app install.",
    },
    {
      icon: Wifi,
      title: "No cloud lock-in",
      body:
        "All perception stays on your LAN. Only text observations + pan images go to Claude. Your own OpenRouter key.",
    },
  ];
  return (
    <section className="container pb-24">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <Card key={it.title} className="transition-colors hover:border-mint/40">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-mint/10 border border-mint/30">
                    <Icon className="h-4 w-4 text-mint" />
                  </div>
                  <CardTitle>{it.title}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-[13.5px] leading-relaxed">
                  {it.body}
                </CardDescription>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      n: "01",
      title: "Perception",
      body: "Phone / webcam + mic stream frames and speech to the backend every few seconds.",
    },
    {
      n: "02",
      title: "Reasoning",
      body:
        "Sonnet 4.6 fuses vision, audio, and plan state — decides whether to act, speak, or stay silent.",
    },
    {
      n: "03",
      title: "Planning (on demand)",
      body:
        "Ask for a recipe → Sonnet calls Opus 4.7, gets a structured cook plan, installs it as state.",
    },
    {
      n: "04",
      title: "Actuation",
      body:
        "Skills fire: set_burner_percent, kill_power, speak, text_user, advance_step, recall.",
    },
  ];
  return (
    <section className="container pb-24">
      <div className="mb-10 max-w-2xl">
        <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">How it works</h2>
        <p className="mt-3 text-muted-foreground">
          A dimos-style module graph: typed streams carry perception into the agent, the agent
          routes tool calls to skills, skills actuate the real world.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s) => (
          <Card key={s.n}>
            <CardHeader>
              <div className="text-xs font-mono text-mint">{s.n}</div>
              <CardTitle className="mt-2">{s.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-[13.5px] leading-relaxed">{s.body}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

function Hardware() {
  return (
    <section id="hardware" className="container pb-24">
      <div className="mb-10 max-w-2xl">
        <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">What you need to buy</h2>
        <p className="mt-3 text-muted-foreground">
          Mise is software-complete without hardware — you can run the full simulator today.
          To point it at a real stove you need exactly one thing (and optionally one more).
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-mint/40">
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <div>
                <Badge variant="mint" className="mb-2">required</Badge>
                <CardTitle>Shelly Plus Plug US</CardTitle>
                <CardDescription className="mt-2">
                  Smart plug with a <strong>local HTTP REST API</strong>, live power monitoring,
                  15A / 1800W. No cloud round-trip. Mise drives it via Gen2 RPC.
                </CardDescription>
              </div>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-mint/10 border border-mint/30">
                <Flame className="h-5 w-5 text-mint" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold">$22.99</span>
              <span className="text-sm text-muted-foreground">at Home Depot</span>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <Link
                href="https://www.homedepot.com/p/Shelly-Plus-Plug-US-WiFi-and-Bluetooth-Operated-Smart-Plug-With-Power-Measurement-Home-Automation-Remote-Control-Shelly-Plus-Plug-US-1/327539186"
                target="_blank"
                rel="noreferrer"
              >
                <Button size="sm">buy at home depot</Button>
              </Link>
              <Link href="https://us.shelly.com/products/shelly-plus-plug-us" target="_blank" rel="noreferrer">
                <Button size="sm" variant="outline">shelly direct</Button>
              </Link>
              <Link
                href="https://www.amazon.com/Shelly-Measurement-Automation-Compatible-Appliances/dp/B0D6GNQMDG"
                target="_blank"
                rel="noreferrer"
              >
                <Button size="sm" variant="outline">amazon</Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <div>
                <Badge variant="outline" className="mb-2">optional</Badge>
                <CardTitle>Amazon Basics 1800W induction burner</CardTitle>
                <CardDescription className="mt-2">
                  Only if you don't already have an electric cooktop. Any electric kettle, hot
                  plate, or toaster works for the first demo.
                </CardDescription>
              </div>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted border border-border/60">
                <Flame className="h-5 w-5 text-muted-foreground" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold">~$50</span>
              <span className="text-sm text-muted-foreground">amazon</span>
            </div>
            <div className="mt-3">
              <Link
                href="https://www.amazon.com/AmazonBasics-1800W-Portable-Induction-Cooktop/dp/B07S2628R9"
                target="_blank"
                rel="noreferrer"
              >
                <Button size="sm" variant="outline">see on amazon</Button>
              </Link>
            </div>
            <p className="mt-4 text-xs text-muted-foreground leading-relaxed">
              Induction requires magnetic cookware (cast iron, magnetic stainless). If your
              pans don't stick to a fridge magnet, use a resistive hot plate instead.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 rounded-lg border border-border/60 bg-card/50 p-5 text-sm">
        <div className="flex items-start gap-3">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-mint/10 border border-mint/30 text-mint font-mono text-xs">
            $
          </div>
          <div>
            <div className="font-medium">Minimum viable spend</div>
            <div className="text-muted-foreground mt-1">
              <strong className="text-foreground">$23</strong> — the Shelly plug + any
              electric appliance you already own. Use a kettle for the first demo; it boils in
              two minutes at 1500W and proves the whole safety loop.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function QuickStart() {
  return (
    <section id="quickstart" className="container pb-24">
      <div className="mb-10 max-w-2xl">
        <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Quick start</h2>
        <p className="mt-3 text-muted-foreground">
          Runs on any laptop with Python 3.11+ and a webcam. No hardware required to try it.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>1. Install</CardTitle>
            <CardDescription>Clone and install the Python package in a venv.</CardDescription>
          </CardHeader>
          <CardContent>
            <CodeBlock>
{`git clone https://github.com/0xbl33p/mise
cd mise
python -m venv .venv && source .venv/Scripts/activate
pip install -e .`}
            </CodeBlock>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>2. Set your OpenRouter key</CardTitle>
            <CardDescription>Mise routes Claude calls through OpenRouter.</CardDescription>
          </CardHeader>
          <CardContent>
            <CodeBlock>
{`echo "OPENROUTER_API_KEY=sk-or-..." > .env`}
            </CodeBlock>
            <p className="mt-3 text-xs text-muted-foreground">
              Grab a key at{" "}
              <Link href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" className="underline underline-offset-4">
                openrouter.ai/keys
              </Link>
              . You pay per token; Sonnet is &lt;$0.01 per minute of cooking.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>3. Try the simulator</CardTitle>
            <CardDescription>No hardware needed. Synthetic stove, full agent loop.</CardDescription>
          </CardHeader>
          <CardContent>
            <CodeBlock>
{`mise run sim --agent claude --images --duration 60`}
            </CodeBlock>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>4. Serve the phone UI</CardTitle>
            <CardDescription>
              Open <code className="rounded bg-muted px-1 py-0.5 text-[12.5px]">https://&lt;your-lan-ip&gt;:8080</code>{" "}
              on your phone.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CodeBlock>
{`mise serve --https --host 0.0.0.0 --plug-ip 192.168.1.XX`}
            </CodeBlock>
            <p className="mt-3 text-xs text-muted-foreground">
              Drop <code className="rounded bg-muted px-1 py-0.5 text-[12.5px]">--plug-ip</code>{" "}
              to run without hardware. Phone will warn about the self-signed cert once —
              tap Advanced → Proceed.
            </p>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="rounded-lg border border-border/60 bg-black/40 p-4 text-[12.5px] leading-relaxed overflow-x-auto">
      <code className="font-mono text-foreground/90">{children}</code>
    </pre>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border/60">
      <div className="container py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Image
            src="/mise-logo.png"
            alt="Mise"
            width={22}
            height={22}
            className="drop-shadow-[0_0_10px_rgba(74,222,128,0.6)]"
          />
          <span className="text-sm text-muted-foreground">
            mise — agentic kitchen copilot
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <Link href={REPO} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5">
            <Github className="h-4 w-4" />
            source
          </Link>
          <Link href={GITHUB_USER} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5">
            <Github className="h-4 w-4" />
            @0xbl33p
          </Link>
        </div>
      </div>
    </footer>
  );
}
