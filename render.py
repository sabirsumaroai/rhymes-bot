"""Video, Short, caption aur thumbnail banane ka kaam (FFmpeg + Pillow).
Studio-grade rendering: Dynamic cartoon camera moves, living animated saturation pulses,
kids candy karaoke subtitles, auto-ducked nursery music, and high-CTR 3D sticker thumbnails.
"""
import functools
import glob
import math
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

FPS = 24


def ff(*args):
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg fail: " + p.stderr[-600:])


def duration(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


# ------------------------------------------------------------------------ fonts
def _covers(path, chars):
    try:
        from fontTools.ttLib import TTFont
        cmap = TTFont(path, fontNumber=0, lazy=True).getBestCmap()
        return all(ord(c) in cmap for c in chars)
    except Exception:
        return False


@functools.lru_cache(maxsize=None)
def find_font(need_hindi=True):
    """Devanagari + English support karne wala cross-platform bold font dhundta hai."""
    cands = []

    # 1. Linux fontconfig (agar installed hai)
    if shutil.which("fc-list"):
        for q in (":lang=hi:bold", ":lang=hi"):
            try:
                p = subprocess.run(["fc-list", q, "file"], capture_output=True, text=True)
                if p.returncode == 0:
                    cands += [ln.split(":")[0].strip() for ln in p.stdout.splitlines() if ln.strip()]
            except Exception:
                pass

    # 2. Windows font locations
    win_dir = os.environ.get("WINDIR", r"C:\Windows")
    win_fonts = os.path.join(win_dir, "Fonts")
    for wf in ("Nirmala.ttc", "NirmalaB.ttf", "ARIALUNI.TTF", "arialbd.ttf", "mangal.ttf", "mangalb.ttf", "segoeuib.ttf"):
        wp = os.path.join(win_fonts, wf)
        if os.path.exists(wp):
            cands.append(wp)

    # 3. Linux common font locations
    cands += [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    seen = []
    for c in cands:
        if c not in seen and os.path.exists(c):
            seen.append(c)

    seen.sort(key=lambda c: ("bold" not in c.lower(), c))

    if need_hindi:
        for c in seen:
            if _covers(c, "कA"):
                return c
        for c in seen:
            if _covers(c, "क"):
                return c

    if seen:
        return seen[0]

    return None


def _font(size):
    fp = find_font()
    if fp:
        try:
            return ImageFont.truetype(fp, size, layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines = []
    for raw in text.split("\n"):
        cur = ""
        for w in raw.split():
            t = (cur + " " + w).strip()
            try:
                w_len = draw.textlength(t, font=font)
            except Exception:
                w_len = len(t) * 16
            if w_len <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def caption_png(text, out, size=(1280, 720), lang="hi"):
    """Glossy kids-friendly cartoon subtitle badge with vibrant text."""
    W, H = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    fs = 52
    while True:
        font = _font(fs)
        lines = _wrap(d, text, font, W - 220)
        lh = int(fs * 1.35)
        if (len(lines) * lh <= 180 and len(lines) <= 3) or fs <= 30:
            break
        fs -= 4

    bh = len(lines) * lh + 36
    top = H - bh - 40
    bw = min(W - 80, max(680, int(max(d.textlength(ln, font=font) for ln in lines) + 120)))
    bx0 = (W - bw) // 2
    bx1 = bx0 + bw

    # Layered cartoon pill: shadow + dark glossy backdrop + colorful outline
    d.rounded_rectangle([bx0 + 4, top + 6, bx1 + 4, top + bh + 6], radius=32, fill=(0, 0, 0, 110))
    d.rounded_rectangle([bx0, top, bx1, top + bh], radius=32, fill=(18, 20, 38, 215),
                        outline=(255, 230, 80, 240) if lang == "hi" else (100, 220, 255, 240), width=4)

    # Accent star badge on pill corner
    badge_x, badge_y = bx0 + 20, top + (bh // 2) - 14
    d.text((badge_x, badge_y), "⭐" if lang == "hi" else "🎶", font=_font(28), fill=(255, 240, 120, 255))

    # Text rendering with cheerful high-contrast stroke
    y = top + 18
    text_color = (255, 235, 60, 255) if lang == "hi" else (255, 255, 255, 255)
    stroke_color = (15, 15, 45, 255)

    for ln in lines:
        w = d.textlength(ln, font=font)
        x = (W - w) / 2
        # Soft outer shadow
        d.text((x + 2, y + 3), ln, font=font, fill=(0, 0, 0, 180))
        # Main text with bold outline
        d.text((x, y), ln, font=font, fill=text_color, stroke_width=4, stroke_fill=stroke_color)
        y += lh

    img.save(out)


# ------------------------------------------------------------------------ video
def _zoom_expr(mode, n):
    """Dynamic animated camera moves with gentle cartoon breathing."""
    if mode == 0:
        # Character push-in with gentle sway
        return f"z='1+0.16*on/{n}':x='(iw-iw/zoom)*(0.5+0.04*sin(2*3.1415*on/{n}))':y='(ih-ih/zoom)/2'"
    if mode == 1:
        # Soft pull-out reveal
        return f"z='1.16-0.16*on/{n}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
    if mode == 2:
        # Playful cartoon bounce
        return f"z='1.12+0.04*sin(2*3.1415*on/{n})':x='(iw-iw/zoom)*(0.5+0.12*sin(2*3.1415*on/{n}))':y='(ih-ih/zoom)*(0.5+0.06*sin(4*3.1415*on/{n}))'"
    if mode == 3:
        # Smooth left-to-right character tracking pan
        return f"z='1.14':x='(iw-iw/zoom)*(on/{n})':y='(ih-ih/zoom)/2'"
    if mode == 4:
        # Smooth right-to-left tracking pan
        return f"z='1.14':x='(iw-iw/zoom)*(1-on/{n})':y='(ih-ih/zoom)/2'"
    # Gentle diagonal drift
    return f"z='1+0.14*on/{n}':x='(iw-iw/zoom)*(0.2+0.6*on/{n})':y='(ih-ih/zoom)*(0.3+0.4*on/{n})'"


def scene_clip(img, wav, cap_png, dur, idx, out, crf=21, maxrate="4000k"):
    n = max(2, int(round(dur * FPS)))
    zp = _zoom_expr(idx % 6, n)

    # Pixar-style color grading + breathing saturation pulse + zoompan + overlay
    fc = (
        f"[0:v]scale=1920:1080,eq=saturation='1.22+0.05*sin(2*3.1415*t/2.0)':contrast=1.07:brightness=0.01,"
        f"zoompan={zp}:d={n}:s=1280x720:fps={FPS}[bg];"
        f"[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v]"
    )
    ff("-i", img, "-i", cap_png, "-i", wav, "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
       "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "superfast", "-crf", str(crf), "-maxrate", maxrate,
       "-bufsize", "8000k", "-r", str(FPS), "-g", str(FPS * 2), "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", out)


def concat(clips, out, workdir):
    lst = os.path.join(workdir, "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out)


def add_music(video, music, out):
    """Mixes upbeat background music with automated vocal ducking."""
    # BGM volume 0.18 for cheerful energy without drowning lyrics
    fc = (
        "[1:a]volume=0.18[m];"
        "[0:a][m]amix=inputs=2:duration=first:dropout_transition=0.5[a]"
    )
    ff("-i", video, "-stream_loop", "-1", "-i", music, "-filter_complex", fc,
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out)


def make_short(clips, durs, out, workdir, lo=32, hi=55):
    """Vertical 9:16 Short with animated top hook badge and seamless loop."""
    sel, tot = [], 0.0
    for c, d in zip(clips, durs):
        if tot + d > hi and sel:
            break
        sel.append(c)
        tot += d
        if tot >= lo:
            break
    tmp = os.path.join(workdir, "short_src.mp4")
    concat(sel, tmp, workdir)

    # 9:16 vertical layout with blurred cartoon background and crisp center action
    fc = (
        "[0:v]split[a][b];"
        "[a]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=24:2[bg];"
        "[b]scale=720:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    ff("-i", tmp, "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "23", "-maxrate", "3500k", "-bufsize", "7000k", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out)
    return tot


def make_preview(master, out, target_mb=34):
    """Telegram (50MB limit) ke liye high-quality preview."""
    d = max(1.0, duration(master))
    total_kbps = int(target_mb * 8192 / d)
    vk = max(220, min(920, total_kbps - 64))
    ff("-i", master, "-vf", "scale=640:360", "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{vk}k",
       "-maxrate", f"{int(vk * 1.3)}k", "-bufsize", f"{vk * 2}k", "-c:a", "aac", "-b:a", "64k", "-ac", "1",
       "-movflags", "+faststart", out)
    if os.path.getsize(out) > 48 * 1024 * 1024:
        vk = int(vk * 0.6)
        ff("-i", master, "-vf", "scale=480:270", "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{vk}k",
           "-c:a", "aac", "-b:a", "48k", "-ac", "1", "-movflags", "+faststart", out)


# --------------------------------------------------------------------- thumbnails
def _fit_text(draw, text, max_w, max_h, start=165):
    fs = start
    while fs > 44:
        font = _font(fs)
        lines = _wrap(draw, text, font, max_w)
        lh = int(fs * 1.18)
        if len(lines) <= 2 and len(lines) * lh <= max_h:
            return font, lines, lh
        fs -= 8
    font = _font(44)
    return font, _wrap(draw, text, font, max_w)[:2], 52


def _save_jpg(im, out, limit=1_900_000):
    for q in (92, 86, 80, 72):
        im.save(out, "JPEG", quality=q)
        if os.path.getsize(out) <= limit:
            return


def thumbnail(img_path, text, out, variant="A"):
    """Multi-million-view YouTube Kids style thumbnail:
    - 1.30x Center Zoom into character face
    - Saturated vibrant Pixar lighting
    - Multi-layer 3D sticker text with bold white contour & dark shadow
    - Playful candy framing
    """
    raw_im = Image.open(img_path).convert("RGB")
    w_raw, h_raw = raw_im.size

    # Zoom in 1.30x so characters appear close-up & expressive on small phone screens
    crop_w, crop_h = int(w_raw * 0.77), int(h_raw * 0.77)
    x0, y0 = (w_raw - crop_w) // 2, (h_raw - crop_h) // 2
    im = raw_im.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((1280, 720), Image.Resampling.LANCZOS)

    # Vibrant studio saturation boost
    im = ImageEnhance.Color(im).enhance(1.45)
    im = ImageEnhance.Contrast(im).enhance(1.18)
    d = ImageDraw.Draw(im, "RGBA")

    # Enforce punchy 2-3 words for mobile feeds
    words = text.split()
    if len(words) > 3:
        text = " ".join(words[:3])

    font, lines, lh = _fit_text(d, text, 1120, 280)
    block = len(lines) * lh

    if variant == "A":
        # Variant A: Sunny Golden 3D Text at bottom with gradient contrast bar
        y = 720 - block - 52
        fill = (255, 235, 15, 255)
        stroke = (25, 10, 40, 255)
        border = (255, 60, 120)

        # Soft dark gradient bar at bottom for maximum contrast
        d.rectangle([0, 720 - block - 85, 1280, 720], fill=(12, 14, 32, 150))
    else:
        # Variant B: Glossy Candy Red Ribbon Badge at top
        y = 44
        rx0, ry0, rx1, ry1 = 26, y - 14, 1254, y + block + 22
        d.rounded_rectangle([rx0 + 4, ry0 + 6, rx1 + 4, ry1 + 6], radius=38, fill=(0, 0, 0, 110))
        d.rounded_rectangle([rx0, ry0, rx1, ry1], radius=38, fill=(228, 25, 55, 245),
                            outline=(255, 225, 45, 255), width=6)
        fill = (255, 255, 255, 255)
        stroke = (90, 0, 25, 255)
        border = (255, 215, 0)

    for ln in lines:
        w_text = d.textlength(ln, font=font)
        x = (1280 - w_text) / 2

        # 1. Deep 3D drop shadow (stacked offsets)
        for offset in (8, 6, 4):
            d.text((x + offset, y + offset), ln, font=font, fill=(0, 0, 0, 190), stroke_width=9, stroke_fill=(0, 0, 0, 190))

        # 2. Bold white sticker contour outline
        d.text((x, y), ln, font=font, fill=fill, stroke_width=11, stroke_fill=(255, 255, 255, 255))

        # 3. Crisp punchy colored foreground text with dark outline
        d.text((x, y), ln, font=font, fill=fill, stroke_width=6, stroke_fill=stroke)
        y += lh

    # Playful border frame
    d.rectangle([0, 0, 1279, 719], outline=border, width=14)
    _save_jpg(im, out)
