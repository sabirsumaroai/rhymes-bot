"""Kids Nursery Rhymes SFX & Foley Engine.
Generates or loads cartoon sound effects (pops, boings, chimes, giggles, splashes, bells)
and dynamically mixes them with TTS scenes and background music.
"""
import math
import os
import random
import struct
import subprocess
import wave

SFX_DIR = "sfx"


def _generate_synthetic_wav(path, sound_type):
    """Procedurally synthesize cute cartoon sound effects in 44100Hz mono WAV."""
    rate = 44100
    samples = []

    if sound_type == "pop":
        # Bubble / pop sound: fast downward pitch sweep with sharp envelope
        dur = 0.09
        total = int(rate * dur)
        for i in range(total):
            t = i / rate
            f = 850 - 650 * (i / total) ** 0.5
            amp = math.exp(-28 * t)
            samples.append(math.sin(2 * math.pi * f * t) * amp)

    elif sound_type == "boing":
        # Cartoon spring bounce: vibrating pitch
        dur = 0.35
        total = int(rate * dur)
        for i in range(total):
            t = i / rate
            f = 220 + 200 * math.sin(2 * math.pi * 14 * t) * math.exp(-4 * t)
            amp = math.exp(-6 * t)
            samples.append(math.sin(2 * math.pi * f * t) * amp)

    elif sound_type == "chime" or sound_type == "twinkle":
        # Sweet magical chimes: pentatonic arpeggio (C6, E6, G6, C7)
        dur = 0.65
        total = int(rate * dur)
        freqs = [1046.5, 1318.5, 1567.98, 2093.0]
        for i in range(total):
            t = i / rate
            val = 0.0
            for k, f in enumerate(freqs):
                delay = k * 0.09
                if t >= delay:
                    dt = t - delay
                    amp = math.exp(-7 * dt)
                    val += math.sin(2 * math.pi * f * dt) * amp * 0.3
            samples.append(val)

    elif sound_type == "ding" or sound_type == "bell":
        # Sweet xylophone / bell ding
        dur = 0.4
        total = int(rate * dur)
        for i in range(total):
            t = i / rate
            f1, f2 = 880.0, 1760.0
            amp = math.exp(-8 * t)
            samples.append((0.7 * math.sin(2 * math.pi * f1 * t) + 0.3 * math.sin(2 * math.pi * f2 * t)) * amp)

    elif sound_type == "whoosh":
        # Playful air swoosh (transition)
        dur = 0.28
        total = int(rate * dur)
        for i in range(total):
            t = i / rate
            envelope = math.sin(math.pi * (i / total))
            noise = random.uniform(-1, 1)
            samples.append(noise * envelope * 0.45)

    elif sound_type == "cheer":
        # High pitched celebration chime
        dur = 0.5
        total = int(rate * dur)
        for i in range(total):
            t = i / rate
            f = 587.33 + 400 * (i / total)
            amp = math.sin(math.pi * (i / total))
            samples.append(math.sin(2 * math.pi * f * t) * amp * 0.6)

    else:
        # Default cute chirp
        dur = 0.15
        total = int(rate * dur)
        for i in range(total):
            t = i / rate
            f = 600 + 400 * (i / total)
            amp = math.exp(-12 * t)
            samples.append(math.sin(2 * math.pi * f * t) * amp)

    # Normalize and write 16-bit PCM WAV
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        raw = bytearray()
        for s in samples:
            val = max(-1.0, min(1.0, s))
            raw += struct.pack("<h", int(val * 32767))
        wf.writeframes(raw)


def ensure_sfx_catalog():
    """Ensure basic sound effects exist in sfx/ directory."""
    os.makedirs(SFX_DIR, exist_ok=True)
    needed = ["pop", "boing", "chime", "ding", "whoosh", "cheer"]
    for s in needed:
        target = os.path.join(SFX_DIR, f"{s}.wav")
        if not os.path.exists(target):
            try:
                _generate_synthetic_wav(target, s)
            except Exception as e:
                print(f"[sfx] could not generate {s}: {e}")


def match_sfx_for_scene(scene_text, image_prompt, chorus=False):
    """Detect which cartoon SFX matches the mood/action of this scene."""
    ensure_sfx_catalog()
    blob = f"{scene_text} {image_prompt}".lower()

    if chorus:
        return os.path.join(SFX_DIR, "cheer.wav") if os.path.exists(os.path.join(SFX_DIR, "cheer.wav")) else None

    # Keyword mapping to sound effects
    if any(k in blob for k in ("jump", "bounce", "hop", "dance", "run", "fast", "kood", "naach")):
        name = "boing"
    elif any(k in blob for k in ("star", "moon", "magic", "clean", "sparkle", "shine", "chaand", "taare", "sundar")):
        name = "chime"
    elif any(k in blob for k in ("1", "2", "3", "4", "5", "count", "ginti", "number", "ek", "do", "teen")):
        name = "ding"
    elif any(k in blob for k in ("fly", "swoop", "train", "car", "gaadi", "chidiya", "hawa", "wind")):
        name = "whoosh"
    elif any(k in blob for k in ("bubble", "pop", "fruit", "rang", "color", "ball", "gubbara", "seb", "aam")):
        name = "pop"
    else:
        name = random.choice(["pop", "ding", "chime"])

    p = os.path.join(SFX_DIR, f"{name}.wav")
    return p if os.path.exists(p) else None


def overlay_sfx_on_audio(tts_wav, sfx_wav, out_wav, delay_sec=0.15, sfx_vol=0.75):
    """Mixes a sound effect at an offset into the TTS audio."""
    if not sfx_wav or not os.path.exists(sfx_wav):
        return tts_wav

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", tts_wav,
        "-i", sfx_wav,
        "-filter_complex",
        f"[1:a]adelay={int(delay_sec * 1000)}|{int(delay_sec * 1000)},volume={sfx_vol}[sfx];"
        f"[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=0[a]",
        "-map", "[a]",
        "-ar", "44100", "-ac", "1",
        out_wav
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode == 0 and os.path.exists(out_wav) and os.path.getsize(out_wav) > 100:
        return out_wav
    return tts_wav
