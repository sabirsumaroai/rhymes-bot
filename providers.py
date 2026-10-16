"""Har cheez ke liye fallback chain: LLM (script), Image, TTS (voice).
Ek provider fail ho to agla apne aap try hota hai. Ye file network wali saari cheezein sambhalti hai."""
import asyncio
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import time
import urllib.parse

import requests

DRY = os.getenv("DRY_RUN") == "1"
CACHE_DIR = os.path.join("cache", "images")


class ProviderError(Exception):
    pass


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def extract_json(text):
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("response me JSON nahi mila")
    return json.loads(text[s:e + 1])


# --------------------------------------------------------------------------- LLM
BACKOFF = [5, 20, 60]


def _gemini_call(model, prompt, key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json", "maxOutputTokens": 8192},
    }
    return requests.post(url, headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                         json=body, timeout=120)


def _openai_call(base_url, model, prompt, key):
    return requests.post(base_url.rstrip("/") + "/chat/completions",
                         headers={"Authorization": f"Bearer {key}"},
                         json={"model": model, "temperature": 1.0, "max_tokens": 7000,
                               "messages": [{"role": "user", "content": prompt}]}, timeout=120)


def _gemini_text(r):
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _openai_text(r):
    return r.json()["choices"][0]["message"]["content"]


def _try_provider(label, call, get_text, validate):
    """Ek provider ko retry ke saath chalata hai. Seedha data return karta hai ya None."""
    for attempt, wait in enumerate(BACKOFF + [None]):
        try:
            r = call()
        except requests.RequestException as e:
            log(f"[llm] {label}: network error {e}")
            r = None
        if r is not None:
            if r.status_code == 200:
                try:
                    data = extract_json(get_text(r))
                    validate(data)
                    return data
                except Exception as e:  # kharab JSON / validation fail
                    log(f"[llm] {label}: output theek nahi ({e})")
                    if attempt >= 1:
                        return None
                    continue
            if r.status_code in (400, 401, 403, 404):
                log(f"[llm] {label}: HTTP {r.status_code} - ye provider skip")
                return None
            log(f"[llm] {label}: HTTP {r.status_code} (limit/server) - retry")
        if wait is None:
            return None
        time.sleep(wait)
    return None


def generate_script(prompt, cfg, validate):
    """Gemini models -> fallback providers. Pehla valid result return hota hai."""
    if DRY:
        from dry import fake_script
        return fake_script(prompt), "dry"
    gkey = os.getenv("GEMINI_API_KEY", "")
    if gkey:
        for model in cfg["gemini_models"]:
            data = _try_provider(f"gemini/{model}", lambda m=model: _gemini_call(m, prompt, gkey),
                                 _gemini_text, validate)
            if data:
                return data, f"gemini/{model}"
    for fb in cfg.get("fallback_llms", []):
        key = os.getenv(fb["key_env"], "")
        if not key:
            continue
        data = _try_provider(fb["name"], lambda f=fb, k=key: _openai_call(f["base_url"], f["model"], prompt, k),
                             _openai_text, validate)
        if data:
            return data, fb["name"]
    raise ProviderError("koi bhi LLM provider script nahi de paya")


def simple_text(prompt, cfg):
    """Weekly report ke liye: JSON dict wapas (same chain)."""
    return generate_script(prompt, cfg, lambda d: None)


# ------------------------------------------------------------------------- Image
_last_img_call = [0.0]


def _valid_image(path):
    from PIL import Image
    try:
        with Image.open(path) as im:
            im.load()
            return im.width >= 256 and im.height >= 256
    except Exception:
        return False


def _pollinations(prompt, seed, out):
    key = os.getenv("POLLINATIONS_KEY", "")
    q = urllib.parse.quote(prompt[:900])
    if key:
        url = f"https://gen.pollinations.ai/image/{q}?width=1280&height=720&seed={seed}&nologo=true&model=flux&key={key}"
    else:
        url = f"https://image.pollinations.ai/prompt/{q}?width=1280&height=720&seed={seed}&nologo=true&model=flux"
    r = requests.get(url, timeout=180)
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
        raise ProviderError(f"pollinations HTTP {r.status_code}")
    with open(out, "wb") as f:
        f.write(r.content)
    if not _valid_image(out):
        raise ProviderError("pollinations ne kharab image di")


def _throttle(cfg):
    gap = cfg["image"]["min_interval_key_sec"] if os.getenv("POLLINATIONS_KEY") else cfg["image"]["min_interval_anon_sec"]
    wait = _last_img_call[0] + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_img_call[0] = time.time()


def _cache_path(prompt, seed):
    return os.path.join(CACHE_DIR, hashlib.sha1(f"{prompt}|{seed}".encode()).hexdigest() + ".jpg")


def prune_cache(cfg):
    if not os.path.isdir(CACHE_DIR):
        return
    files = sorted((os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR)), key=os.path.getmtime, reverse=True)
    for f in files[cfg["image"]["cache_max_files"]:]:
        try:
            os.remove(f)
        except OSError:
            pass


def fallback_art(out, idx, text=""):
    """Last resort: Pillow se simple cartoon-jaisa scene (hamesha chalta hai, internet nahi chahiye)."""
    from PIL import Image, ImageDraw
    rnd = random.Random(idx * 7919 + len(text))
    pals = [((135, 206, 250), (255, 250, 205), (110, 200, 120)), ((255, 183, 197), (255, 240, 200), (150, 215, 140)),
            ((173, 216, 230), (255, 228, 181), (120, 190, 130)), ((196, 181, 253), (254, 249, 195), (134, 239, 172))]
    top, sun, hill = rnd.choice(pals)
    W, H = 1280, 720
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] * (1 - t) + 255 * t) for i in range(3)))
    sx, sy = rnd.randint(150, 1100), rnd.randint(90, 220)
    d.ellipse([sx - 80, sy - 80, sx + 80, sy + 80], fill=sun)
    for _ in range(3):
        cx, cy = rnd.randint(100, 1180), rnd.randint(60, 300)
        for dx in (-50, 0, 50):
            d.ellipse([cx + dx - 55, cy - 30, cx + dx + 55, cy + 30], fill=(255, 255, 255))
    for k in range(3):
        base = 470 + k * 70
        shade = tuple(max(0, c - k * 22) for c in hill)
        d.ellipse([-200 + k * 300, base, 700 + k * 300, base + 600], fill=shade)
    for _ in range(9):
        fx, fy = rnd.randint(40, 1240), rnd.randint(520, 700)
        d.ellipse([fx - 14, fy - 14, fx + 14, fy + 14], fill=rnd.choice([(255, 99, 132), (255, 205, 86), (255, 255, 255)]))
        d.ellipse([fx - 5, fy - 5, fx + 5, fy + 5], fill=(255, 200, 0))
    im.save(out, quality=90)


def get_image(prompt, seed, idx, text, cfg, workdir):
    """(path, source) wapas. Order: cache -> Pollinations -> purani cache image -> Pillow art."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    out = os.path.join(workdir, f"img_{idx:03d}.jpg")
    cp = _cache_path(prompt, seed)
    if os.path.exists(cp):
        shutil.copy(cp, out)
        return out, "cache"
    if not DRY:
        for attempt in range(3):
            try:
                _throttle(cfg)
                _pollinations(prompt, seed, out)
                shutil.copy(out, cp)
                return out, "pollinations"
            except Exception as e:
                log(f"[img {idx}] pollinations fail ({e}), try {attempt + 1}/3")
                time.sleep(5 * (attempt + 1))
        old = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR)]
        old = [f for f in old if _valid_image(f)]
        if old:
            shutil.copy(random.choice(old), out)
            return out, "old-cache"
    fallback_art(out, idx, text)
    return out, "pillow-art"


# --------------------------------------------------------------------------- TTS
def _ff(*args):
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise ProviderError("ffmpeg: " + p.stderr[-400:])


def duration(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def _tts_edge(text, voice, out, rate, pitch):
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)
    asyncio.run(asyncio.wait_for(go(), timeout=90))


def _tts_gtts(text, lang, out, tld):
    from gtts import gTTS
    gTTS(text=text, lang=lang, tld=tld if lang == "en" else "com").save(out)


def _tts_espeak(text, lang, out):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise ProviderError("espeak installed nahi")
    subprocess.run([exe, "-v", "hi" if lang == "hi" else "en", "-s", "125", "-w", out, text],
                   check=True, capture_output=True, timeout=60)


def synthesize(text, lang, out_wav, cfg):
    """Text -> wav (44.1k mono, end me thoda silence). (seconds, source) wapas."""
    if DRY:
        from dry import fake_tts
        return fake_tts(text, out_wav)
    clean = re.sub(r"\s*\n\s*", ", ", text.strip())
    tmp = out_wav + ".raw"
    t = cfg["tts"]
    chain = [
        ("edge-tts", 3, lambda: _tts_edge(clean, t["voices"][lang], tmp, t["rate"], t["pitch"])),
        ("gtts", 2, lambda: _tts_gtts(clean, lang, tmp, t["gtts_tld"])),
        ("espeak", 1, lambda: _tts_espeak(clean, lang, tmp)),
    ]
    last = None
    for name, tries, fn in chain:
        for k in range(tries):
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
                fn()
                _ff("-i", tmp, "-ar", "44100", "-ac", "1", "-af", "apad=pad_dur=0.45", out_wav)
                d = duration(out_wav)
                if d < 0.8:
                    raise ProviderError("audio bahut chhota")
                os.remove(tmp)
                return d, name
            except Exception as e:
                last = e
                log(f"[tts] {name} fail ({e}) try {k + 1}/{tries}")
                time.sleep(2 * (k + 1))
    raise ProviderError(f"koi TTS provider nahi chala: {last}")
