"""Deterministic motion of the repository Little Shrew rig (first episode only).

Local media authoring, not a model provider, scheduler or WRE admission owner.
Uses the exact shared SVG definitions; no external artwork or audio recordings.
"""
from __future__ import annotations

import io
import math
from pathlib import Path
import subprocess
import tempfile
import wave
import xml.etree.ElementTree as ET

import cairosvg
import numpy as np
from PIL import Image

NS = "http://www.w3.org/2000/svg"
WIDTH, HEIGHT, FPS = 960, 540, 30


class ShrewScene:
    """One fixed set and five instances of the same rig, sampled by absolute time."""

    def __init__(self, rig_path):
        root = ET.fromstring(Path(rig_path).read_bytes())
        self.defs = ET.tostring(root.find(f"{{{NS}}}defs"), encoding="unicode")

    def svg(self, seconds):
        if not math.isfinite(seconds) or not 0 <= seconds < 15:
            raise ValueError("Only first-episode times in [0, 15) are supported")
        t = seconds
        # Revision 2: a brief tremor wakes only the rightmost of three children.
        progress = min(1, max(0, (t - 3.2) / 2.3))
        progress = progress * progress * (3 - 2 * progress)
        hero_x = 350 + 410 * progress
        hero_y = 346 - (4 * abs(math.sin((t - 3.2) * 13)) if 3.2 < t < 5.5 else 0)
        hero_expression = "sleepy" if t < 2.1 else "neutral"
        tremor = 2.5 * math.sin(t * 42) * math.sin(math.pi * (t - 1) / .9) if 1 < t < 1.9 else 0
        bodies = []
        placements = [(75, 202, 1.12), (290, 192, 1.2),
                      (120, 346, .42), (235, 346, .42), (hero_x, hero_y, .42)]
        for i, (x, y, scale) in enumerate(placements):
            expression = hero_expression if i == 4 else "sleepy"
            breathe = 1.3 * math.sin(t * math.pi + i * .4)
            tilt = 0
            if i == 4:
                if 1.9 < t < 3.2:
                    tilt = 8 * math.sin((t - 1.9) * 16) * math.sin(math.pi * (t - 1.9) / 1.3)
                elif 3.2 <= t < 5.5:
                    tilt = 4 * math.sin((t - 3.2) * 13)
                elif 5.5 <= t < 14:
                    tilt = 3 * max(0, math.sin((t - 5.5) * 7))
            bodies.append(f'<g data-character="{i}" transform="translate({x:.3f},{y+breathe:.3f}) '
                          f'scale({scale}) rotate({tilt:.3f},91,100)">'
                          f'<use href="#{expression}" xlink:href="#{expression}"/></g>')
        pebbles = []
        for i, x in enumerate((490, 555, 620)):
            bounce = 3 * abs(tremor)
            pebbles.append(f'<ellipse cx="{x}" cy="{416-bounce:.3f}" rx="{6+i}" ry="4" fill="#9C724F"/>')
        return (f'<svg xmlns="{NS}" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">{self.defs}'
                '<rect width="960" height="540" fill="#D9B78B"/>'
                f'<g transform="translate({tremor:.3f},0)">'
                '<path d="M30 430 L30 260 Q30 95 230 100 L610 100 Q725 100 730 230 '
                'Q900 200 930 325 L930 430 Z" fill="#FFF4D9"/>'
                '<path d="M30 430 H930" stroke="#9C724F" stroke-width="5"/>'
                '<path d="M850 235 Q825 290 834 370 M839 302 Q805 275 797 292 '
                'M839 284 Q868 255 877 275" fill="none" stroke="#789468" '
                'stroke-width="7" stroke-linecap="round"/>'
                + "".join(pebbles + bodies) + '</g></svg>')

    def frame(self, seconds):
        png = cairosvg.svg2png(bytestring=self.svg(seconds).encode())
        return Image.open(io.BytesIO(png)).convert("RGB")


def render_shot(scene, beat_index, output):
    """Encode 150 distinct-time frames; exclusive publication, bounded subprocess."""
    if type(beat_index) is not int or beat_index not in range(3):
        raise ValueError("Only beats 0, 1 and 2 are implemented")
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    # Frames stay on disk so a blocked encoder cannot deadlock a raw-video pipe.
    with tempfile.TemporaryDirectory(prefix="shrew-frames-", dir=output.parent) as temp:
        temp = Path(temp)
        for frame in range(150):
            scene.frame(beat_index * 5 + frame / FPS).save(temp / f"{frame:03d}.png")
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-framerate", str(FPS), "-i", str(temp / "%03d.png"),
                        "-frames:v", "150", "-c:v", "libx264", "-threads", "2",
                        "-pix_fmt", "yuv420p", "-crf", "18", str(temp / "shot.mp4")],
                       check=True, capture_output=True, timeout=120)
        import os
        os.link(temp / "shot.mp4", output)


def compose_audio(output):
    """Original 120 BPM flute-like score plus quiet synthesized snore/sniff/rumble.

    No sampled recordings, voices or borrowed melody. Returns actual cue windows.
    """
    rate = 48000
    audio = np.zeros(rate * 15, dtype=np.float64)
    rng = np.random.default_rng(120)

    def tone(start, length, frequency, gain):
        start, count = round(start * rate), round(length * rate)
        t = np.arange(count) / rate
        envelope = np.sin(np.pi * np.minimum(1, t / length)) ** 2
        audio[start:start+count] += gain * envelope * (
            np.sin(2 * np.pi * frequency * t) + .12 * np.sin(4 * np.pi * frequency * t))

    # Authored pitch/rhythm sequence; space around the story's sound cues.
    for start, note in ((0, 72), (1, 76), (2, 74), (3.5, 79), (5, 76),
                        (6.5, 79), (8, 81), (9, 76), (12, 74), (13.5, 72)):
        tone(start, .8, 440 * 2 ** ((note - 69) / 12), .10)
    for start in np.arange(0, 10, .5):
        tone(float(start), .08, 180, .035)
    for start in (.15,):
        tone(start, .65, 115, .08)
        tone(start, .65, 145, .025)
    for start in (5.8, 6.3, 6.8, 8.3, 8.8, 9.3, 11.3, 11.8, 12.3):
        n = int(.22 * rate)
        noise = rng.normal(0, .08, n)
        noise = np.convolve(noise, np.ones(8) / 8, mode="same")
        audio[int(start*rate):int(start*rate)+n] += noise * np.sin(np.linspace(0, np.pi, n)) ** 2
    tone(1.0, .9, 65, .08)
    tone(1.0, .9, 83, .035)
    # Leave headroom, never normalize a quiet event into a startling peak.
    if np.max(np.abs(audio)) >= .8:
        raise ValueError("Unexpected soundtrack peak")
    with Path(output).open("xb") as target, wave.open(target, "wb") as wav:
        wav.setparams((1, 2, rate, len(audio), "NONE", "not compressed"))
        wav.writeframes((audio * 32767).astype("<i2").tobytes())
    return [{"start": .1, "end": .9, "text": "[soft snoring]"},
            {"start": 1.0, "end": 1.9, "text": "[gentle rumble]"},
            {"start": 5.8, "end": 7.2, "text": "[sniff, sniff, sniff]"},
            {"start": 8.3, "end": 9.7, "text": "[sniff, sniff, sniff]"},
            {"start": 11.3, "end": 12.7, "text": "[sniff, sniff, sniff]"}]
