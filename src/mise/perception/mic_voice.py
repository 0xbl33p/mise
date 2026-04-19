from __future__ import annotations

import asyncio
import queue
from typing import TYPE_CHECKING

import numpy as np
from rich.console import Console

from mise.core.module import Module
from mise.core.stream import Out
from mise.messages import UserUtterance

if TYPE_CHECKING:
    from mise.audio.gate import AudioGate

console = Console()

SR = 16000  # faster-whisper expects 16kHz
FRAME_MS = 30
FRAME_SAMPLES = int(SR * FRAME_MS / 1000)  # 480

# Energy VAD hyperparameters
SPEECH_RMS = 0.012  # above this = potential speech
START_FRAMES = 3  # need N consecutive speech frames to latch on
SILENCE_HANG_MS = 800  # trailing silence after speech to close an utterance
PREROLL_MS = 400  # keep this much pre-speech audio in the final clip
MIN_UTTER_MS = 350  # drop anything shorter than this (likely noise)
MAX_UTTER_MS = 20_000  # force-close runaway segments


class MicVoice(Module):
    """Always-on microphone + faster-whisper STT.

    Streams audio from the default input device, uses a simple energy-based VAD to chunk
    utterances, and transcribes each chunk via `small.en`. Publishes UserUtterance on a stream
    the agent consumes.
    """

    utter = Out(UserUtterance)

    def __init__(
        self,
        audio_gate: "AudioGate | None" = None,
        model_size: str = "small.en",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        super().__init__()
        self.audio_gate = audio_gate
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._raw_q: queue.Queue = queue.Queue()
        self._preroll = np.zeros(int(SR * PREROLL_MS / 1000), dtype=np.float32)

    async def run(self) -> None:
        import sounddevice as sd  # noqa: PLC0415
        from faster_whisper import WhisperModel  # noqa: PLC0415

        console.log(f"[mic] loading faster-whisper {self.model_size} on {self.device}/{self.compute_type}")
        self._model = WhisperModel(
            self.model_size, device=self.device, compute_type=self.compute_type
        )
        console.log("[mic] model ready — always-on listening engaged")

        def _cb(indata, frames, time_info, status):  # noqa: ANN001, ARG001
            if status:
                console.log(f"[mic] status: {status}")
            self._raw_q.put(indata[:, 0].copy())

        stream = sd.InputStream(
            samplerate=SR,
            channels=1,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            callback=_cb,
        )
        stream.start()
        try:
            await self._vad_loop()
        finally:
            stream.stop()
            stream.close()

    async def _vad_loop(self) -> None:
        loop = asyncio.get_event_loop()
        in_speech = False
        speech_latch = 0
        silence_ms = 0
        utter_ms = 0
        buf: list[np.ndarray] = []
        preroll = self._preroll.copy()

        while True:
            frame = await loop.run_in_executor(None, self._raw_q.get)

            if self.audio_gate is not None and self.audio_gate.mic_should_drop():
                in_speech = False
                speech_latch = 0
                silence_ms = 0
                utter_ms = 0
                buf = []
                preroll = self._preroll.copy()
                continue

            rms = float(np.sqrt(np.mean(frame**2)))
            is_speech = rms > SPEECH_RMS

            if not in_speech:
                preroll = np.concatenate([preroll[FRAME_SAMPLES:], frame])
                if is_speech:
                    speech_latch += 1
                    if speech_latch >= START_FRAMES:
                        in_speech = True
                        buf = [preroll.copy(), frame]
                        utter_ms = PREROLL_MS + FRAME_MS
                        silence_ms = 0
                else:
                    speech_latch = 0
            else:
                buf.append(frame)
                utter_ms += FRAME_MS
                if is_speech:
                    silence_ms = 0
                else:
                    silence_ms += FRAME_MS

                if silence_ms >= SILENCE_HANG_MS or utter_ms >= MAX_UTTER_MS:
                    audio = np.concatenate(buf)
                    in_speech = False
                    speech_latch = 0
                    silence_ms = 0
                    utter_ms = 0
                    buf = []
                    preroll = self._preroll.copy()

                    if (len(audio) / SR) * 1000 < MIN_UTTER_MS:
                        continue
                    text = await loop.run_in_executor(None, self._transcribe, audio)
                    text = (text or "").strip()
                    if not text:
                        continue
                    console.log(f"[mic] heard: {text!r}")
                    await self.utter.publish(UserUtterance(text=text))

    def _transcribe(self, audio: np.ndarray) -> str:
        assert self._model is not None
        segments, _info = self._model.transcribe(
            audio, language="en", vad_filter=False, beam_size=1
        )
        return " ".join(seg.text for seg in segments)
