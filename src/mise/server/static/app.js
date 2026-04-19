// Mise browser client.
// - Opens a WebSocket back to the server.
// - Grabs camera frames and sends them as base64 JPEGs every FRAME_INTERVAL_MS.
// - Uses the browser's SpeechRecognition for push-to-talk STT (free, cloud-backed on Chrome/Safari).
// - Uses SpeechSynthesis to speak Mise's replies aloud.
//
// Works on: Chrome desktop, Chrome Android, Safari iOS 14.5+, Edge. Firefox: no SpeechRecognition.

const FRAME_INTERVAL_MS = 2500;
const JPEG_QUALITY = 0.7;
const CAPTURE_SIZE = 512; // max dimension sent to the backend

const els = {
  video: document.getElementById("cam"),
  capture: document.getElementById("capture"),
  connDot: document.getElementById("conn-dot"),
  connText: document.getElementById("conn-text"),
  burnerWatts: document.getElementById("burner-watts"),
  burnerBar: document.getElementById("burner-bar"),
  planCard: document.getElementById("plan-card"),
  planDish: document.getElementById("plan-dish"),
  planIdx: document.getElementById("plan-idx"),
  planDesc: document.getElementById("plan-desc"),
  transcript: document.getElementById("transcript"),
  micBtn: document.getElementById("mic-btn"),
  textForm: document.getElementById("text-form"),
  textInput: document.getElementById("text-input"),
};

// ------- WebSocket -------
let ws = null;
let wsReady = false;

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    wsReady = true;
    setConn("on", "connected");
    addMsg("system", "connected to mise");
  };
  ws.onclose = () => {
    wsReady = false;
    setConn("", "disconnected");
    setTimeout(connect, 1500);
  };
  ws.onerror = () => setConn("warn", "error");
  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    handle(msg);
  };
}

function send(obj) {
  if (!wsReady || !ws) return;
  try { ws.send(JSON.stringify(obj)); } catch {}
}

function setConn(cls, text) {
  els.connDot.className = "dot" + (cls ? " " + cls : "");
  els.connText.textContent = text;
}

function handle(msg) {
  if (msg.type === "speak") {
    addMsg("agent", msg.message);
    speak(msg.message);
  } else if (msg.type === "text") {
    addMsg("agent", "[text] " + msg.message);
  } else if (msg.type === "burner") {
    updateBurner(msg.watts, msg.on);
  } else if (msg.type === "plan") {
    updatePlan(msg);
  } else if (msg.type === "alert") {
    addAlert(msg.kind, msg.detail);
    speak("Safety alert: " + msg.detail);
  }
}

function addAlert(kind, detail) {
  const el = document.createElement("div");
  el.className = "msg alert";
  el.textContent = `⚠ ${kind}: ${detail}`;
  els.transcript.appendChild(el);
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

function addMsg(role, text) {
  const el = document.createElement("div");
  el.className = "msg " + role;
  el.textContent = text;
  els.transcript.appendChild(el);
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

function updateBurner(watts, on) {
  els.burnerWatts.textContent = on ? Math.round(watts) : 0;
  const pct = Math.min(100, (watts / 1800) * 100);
  els.burnerBar.style.width = pct + "%";
}

function updatePlan(msg) {
  if (!msg.dish || msg.step_index < 0) {
    els.planCard.hidden = true;
    return;
  }
  els.planCard.hidden = false;
  els.planDish.textContent = msg.dish;
  const steps = msg.steps || [];
  const step = steps[msg.step_index];
  els.planIdx.textContent = `${msg.step_index + 1}/${steps.length}`;
  els.planDesc.textContent = step ? step.description : "—";
}

// ------- camera -------
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    els.video.srcObject = stream;
    await els.video.play();
    addMsg("system", "camera ready — streaming frames");
    setInterval(snapAndSend, FRAME_INTERVAL_MS);
  } catch (e) {
    addMsg("system", "no camera access — text still works. " + (e.message || ""));
  }
}

function snapAndSend() {
  if (!wsReady) return;
  const v = els.video;
  if (!v.videoWidth) return;
  const scale = Math.min(1, CAPTURE_SIZE / Math.max(v.videoWidth, v.videoHeight));
  const w = Math.round(v.videoWidth * scale);
  const h = Math.round(v.videoHeight * scale);
  els.capture.width = w;
  els.capture.height = h;
  const ctx = els.capture.getContext("2d");
  ctx.drawImage(v, 0, 0, w, h);
  const dataUrl = els.capture.toDataURL("image/jpeg", JPEG_QUALITY);
  const b64 = dataUrl.split(",")[1];
  send({ type: "frame", image_b64: b64 });
}

// ------- TTS -------
let synth = window.speechSynthesis;
let voice = null;
function pickVoice() {
  const voices = synth.getVoices();
  voice =
    voices.find((v) => /en-US/.test(v.lang) && /Google|Samantha|Karen/i.test(v.name)) ||
    voices.find((v) => /en/.test(v.lang)) ||
    voices[0] ||
    null;
}
if (synth) {
  pickVoice();
  synth.onvoiceschanged = pickVoice;
}

function speak(text) {
  if (!synth) return;
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  if (voice) u.voice = voice;
  u.rate = 1.05;
  synth.speak(u);
}

// ------- STT (push-to-talk via Web Speech API) -------
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null;
let listening = false;

if (SR) {
  rec = new SR();
  rec.lang = "en-US";
  rec.interimResults = false;
  rec.continuous = false;
  rec.onresult = (ev) => {
    const text = Array.from(ev.results).map((r) => r[0].transcript).join(" ").trim();
    if (text) {
      addMsg("user", text);
      send({ type: "utterance", text });
    }
  };
  rec.onend = () => {
    listening = false;
    els.micBtn.setAttribute("aria-pressed", "false");
  };
  rec.onerror = () => {
    listening = false;
    els.micBtn.setAttribute("aria-pressed", "false");
  };
}

function startListen() {
  if (!rec || listening) return;
  try {
    rec.start();
    listening = true;
    els.micBtn.setAttribute("aria-pressed", "true");
  } catch {}
}
function stopListen() {
  if (!rec || !listening) return;
  try { rec.stop(); } catch {}
}

els.micBtn.addEventListener("pointerdown", (e) => { e.preventDefault(); startListen(); });
els.micBtn.addEventListener("pointerup", stopListen);
els.micBtn.addEventListener("pointercancel", stopListen);
els.micBtn.addEventListener("pointerleave", stopListen);

// ------- text fallback -------
els.textForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = els.textInput.value.trim();
  if (!text) return;
  addMsg("user", text);
  send({ type: "utterance", text });
  els.textInput.value = "";
});

// ------- boot -------
connect();
startCamera();

// periodic ping to keep the socket warm behind proxies
setInterval(() => send({ type: "ping" }), 20_000);
