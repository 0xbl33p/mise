"""Tiny PIL-based synthetic pan renderer for VLM path testing.

Deliberately stylised (not photorealistic) so we can feed it into Claude and watch the
VLM reason about state ("I see browning edges", "wisps of smoke above the pan") without
a real webcam. Real mode replaces this with actual webcam frames via the same image_b64
field on StoveFrame.
"""
from __future__ import annotations

import base64
import io
import math
import random

from PIL import Image, ImageDraw, ImageFilter


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _pan_interior_color(temp_c: float) -> tuple[int, int, int]:
    """Cold grey -> warm beige -> golden -> brown -> char."""
    if temp_c < 60:
        return (120, 118, 115)
    if temp_c < 120:
        t = (temp_c - 60) / 60
        return (int(_lerp(120, 210, t)), int(_lerp(118, 180, t)), int(_lerp(115, 140, t)))
    if temp_c < 180:
        t = (temp_c - 120) / 60
        return (int(_lerp(210, 170, t)), int(_lerp(180, 110, t)), int(_lerp(140, 60, t)))
    if temp_c < 230:
        t = (temp_c - 180) / 50
        return (int(_lerp(170, 80, t)), int(_lerp(110, 45, t)), int(_lerp(60, 20, t)))
    t = min(1.0, (temp_c - 230) / 40)
    return (int(_lerp(80, 30, t)), int(_lerp(45, 20, t)), int(_lerp(20, 15, t)))


def render_pan(temp_c: float, size: int = 256, seed: int | None = None) -> bytes:
    """Return a PNG-encoded synthetic top-down view of a pan at the given temperature."""
    rng = random.Random(seed if seed is not None else int(temp_c * 13))
    img = Image.new("RGB", (size, size), (30, 30, 32))  # dark counter
    d = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    pan_r = int(size * 0.42)
    rim_r = int(size * 0.46)

    # Rim (dark metal)
    d.ellipse((cx - rim_r, cy - rim_r, cx + rim_r, cy + rim_r), fill=(55, 55, 58))
    # Interior (temp-colored)
    interior = _pan_interior_color(temp_c)
    d.ellipse((cx - pan_r, cy - pan_r, cx + pan_r, cy + pan_r), fill=interior)

    # Food blobs — a few darker spots
    for _ in range(4):
        bx = cx + rng.randint(-pan_r // 2, pan_r // 2)
        by = cy + rng.randint(-pan_r // 2, pan_r // 2)
        br = rng.randint(10, 22)
        shade = max(0, interior[0] - 40), max(0, interior[1] - 40), max(0, interior[2] - 30)
        d.ellipse((bx - br, by - br, bx + br, by + br), fill=shade)

    # Oil sheen highlights at mid temp
    if 90 < temp_c < 200:
        for _ in range(rng.randint(3, 7)):
            hx = cx + rng.randint(-pan_r // 2, pan_r // 2)
            hy = cy + rng.randint(-pan_r // 2, pan_r // 2)
            hr = rng.randint(3, 7)
            d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=(255, 240, 200))

    # Steam (soft white wisps, above the pan) — 100C..220C
    if 100 < temp_c < 230:
        steam = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sd = ImageDraw.Draw(steam)
        wisps = min(9, int((temp_c - 100) / 20) + 2)
        for _ in range(wisps):
            wx = cx + rng.randint(-pan_r // 2, pan_r // 2)
            wy = cy - pan_r - rng.randint(5, 40)
            wr = rng.randint(14, 28)
            alpha = rng.randint(60, 140)
            sd.ellipse((wx - wr, wy - wr, wx + wr, wy + wr), fill=(240, 240, 240, alpha))
        steam = steam.filter(ImageFilter.GaussianBlur(6))
        img.paste(steam, (0, 0), steam)

    # Smoke (grey, thicker, taller) — >220C
    if temp_c >= 220:
        smoke = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sd = ImageDraw.Draw(smoke)
        intensity = min(1.0, (temp_c - 220) / 40)
        wisps = int(6 + intensity * 10)
        for _ in range(wisps):
            wx = cx + rng.randint(-pan_r, pan_r)
            wy = cy - pan_r - rng.randint(0, 90)
            wr = rng.randint(18, 38)
            grey = rng.randint(70, 130)
            alpha = int(100 + intensity * 120)
            sd.ellipse((wx - wr, wy - wr, wx + wr, wy + wr), fill=(grey, grey, grey, alpha))
        smoke = smoke.filter(ImageFilter.GaussianBlur(10))
        img.paste(smoke, (0, 0), smoke)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_pan_b64(temp_c: float, size: int = 256, seed: int | None = None) -> str:
    return base64.b64encode(render_pan(temp_c, size=size, seed=seed)).decode("ascii")


# Backwards helper: round temp to a smoothed value so the agent gets less jittery frames
def quantise_temp(temp_c: float, step: float = 5.0) -> float:
    return round(temp_c / step) * step


if __name__ == "__main__":  # quick visual sanity check
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "pan_preview.png"
    with open(out, "wb") as f:
        f.write(render_pan(float(sys.argv[2]) if len(sys.argv) > 2 else 180.0))
    print(f"wrote {out}")
