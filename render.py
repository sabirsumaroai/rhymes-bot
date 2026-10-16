"""Video, Short, caption aur thumbnail banane ka kaam (FFmpeg + Pillow)."""
import functools
import os
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
    """Aisa bold font jo Devanagari + English dono dikha sake (Pillow raqm se sahi shaping)."""
    cands = []
    for q in (":lang=hi:bold", ":lang=hi"):
        p = subprocess.run(["fc-list", q, "file"], capture_output=True, text=True)
        cands += [ln.split(":")[0].strip() for ln in p.stdout.splitlines() if ln.strip()]
    cands += ["/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", "/usr/share/fonts/truetype/freefont/FreeSans.ttf"]
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
    for c in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if os.path.exists(c):
            return c
    if seen:
        return seen[0]
    raise RuntimeError("koi font nahi mila (fonts-noto-core / fonts-freefont-ttf install karo)")


def _font(size):
    try:
        return ImageFont.truetype(find_font(), size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype(find_font(), size)


def _wrap(draw, text, font, max_w):
    lines = []
    for raw in text.split("\n"):
        cur = ""
        for w in raw.split():
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=font) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def caption_png(text, out, size=(1280, 720)):
    """Neeche semi-transparent patti me lyrics (static, zoom nahi hota)."""
    W, H = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fs = 54
    while True:
        font = _font(fs)
        lines = _wrap(d, text, font, W - 160)
        lh = int(fs * 1.35)
        if (len(lines) * lh <= 190 and len(lines) <= 3) or fs <= 30:
            break
        fs -= 4
    bh = len(lines) * lh + 30
    top = H - bh - 36
    d.rounded_rectangle([60, top, W - 60, top + bh], radius=28, fill=(0, 0, 0, 120))
    y = top + 15
    for ln in lines:
        w = d.textlength(ln, font=font)
        x = (W - w) / 2
        d.text((x + 2, y + 3), ln, font=font, fill=(0, 0, 0, 200))
        d.text((x, y), ln, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(30, 30, 60, 255))
        y += lh
    img.save(out)


# ------------------------------------------------------------------------ video
def _zoom_expr(mode, n):
    if mode == 0:
        return f"z='1+0.16*on/{n}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
    if mode == 1:
        return f"z='1.16-0.16*on/{n}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
    if mode == 2:
        return f"z='1.14':x='(iw-iw/zoom)*on/{n}':y='(ih-ih/zoom)/2'"
    return f"z='1.14':x='(iw-iw/zoom)*(1-on/{n})':y='(ih-ih/zoom)/2'"


def scene_clip(img, wav, cap_png, dur, idx, out, crf=22, maxrate="3500k"):
    n = max(2, int(round(dur * FPS)))
    zp = _zoom_expr(idx % 4, n)
    fc = (f"[0:v]scale=1920:1080,zoompan={zp}:d={n}:s=1280x720:fps={FPS}[bg];"
          f"[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v]")
    ff("-i", img, "-i", cap_png, "-i", wav, "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
       "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "superfast", "-crf", str(crf), "-maxrate", maxrate,
       "-bufsize", "7000k", "-r", str(FPS), "-g", str(FPS * 2), "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", out)


def concat(clips, out, workdir):
    lst = os.path.join(workdir, "concat.txt")
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out)


def add_music(video, music, out):
    ff("-i", video, "-stream_loop", "-1", "-i", music, "-filter_complex",
       "[1:a]volume=0.10[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out)


def make_short(clips, durs, out, workdir, lo=34, hi=58):
    """Pehle kuch scenes (hook wala hissa) se vertical 9:16 Short, blur background ke saath."""
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
    fc = ("[0:v]split[a][b];[a]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=22:2[bg];"
          "[b]scale=720:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    ff("-i", tmp, "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "24", "-maxrate", "3000k", "-bufsize", "6000k", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out)
    return tot


def make_preview(master, out, target_mb=34):
    """Telegram (50MB limit) ke liye chhota preview."""
    d = max(1.0, duration(master))
    total_kbps = int(target_mb * 8192 / d)
    vk = max(200, min(900, total_kbps - 64))
    ff("-i", master, "-vf", "scale=640:360", "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{vk}k",
       "-maxrate", f"{int(vk * 1.3)}k", "-bufsize", f"{vk * 2}k", "-c:a", "aac", "-b:a", "64k", "-ac", "1",
       "-movflags", "+faststart", out)
    if os.path.getsize(out) > 48 * 1024 * 1024:  # abhi bhi bada ho to aur dabao
        vk = int(vk * 0.6)
        ff("-i", master, "-vf", "scale=480:270", "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{vk}k",
           "-c:a", "aac", "-b:a", "48k", "-ac", "1", "-movflags", "+faststart", out)


# --------------------------------------------------------------------- thumbnails
def _fit_text(draw, text, max_w, max_h, start=170):
    fs = start
    while fs > 40:
        font = _font(fs)
        lines = _wrap(draw, text, font, max_w)
        lh = int(fs * 1.18)
        if len(lines) <= 2 and len(lines) * lh <= max_h:
            return font, lines, lh
        fs -= 8
    font = _font(40)
    return font, _wrap(draw, text, font, max_w)[:2], 48


def _save_jpg(im, out, limit=1_900_000):
    for q in (90, 84, 78, 70):
        im.save(out, "JPEG", quality=q)
        if os.path.getsize(out) <= limit:
            return


def thumbnail(img_path, text, out, variant="A"):
    """1280x720, bright + bada text + border. Variant A: peela text neeche; B: safed text laal patti me upar."""
    im = Image.open(img_path).convert("RGB").resize((1280, 720))
    im = ImageEnhance.Color(im).enhance(1.3)
    im = ImageEnhance.Contrast(im).enhance(1.1)
    d = ImageDraw.Draw(im, "RGBA")
    font, lines, lh = _fit_text(d, text, 1160, 300)
    block = len(lines) * lh
    if variant == "A":
        y = 720 - block - 50
        fill, stroke, border = (255, 221, 0), (20, 20, 20), (255, 64, 129)
    else:
        y = 40
        d.rounded_rectangle([30, y - 10, 1250, y + block + 20], radius=36, fill=(220, 30, 50, 235))
        fill, stroke, border = (255, 255, 255), (90, 0, 15), (255, 214, 0)
    for ln in lines:
        w = d.textlength(ln, font=font)
        d.text(((1280 - w) / 2, y), ln, font=font, fill=fill, stroke_width=9, stroke_fill=stroke)
        y += lh
    d.rectangle([0, 0, 1279, 719], outline=border, width=16)
    _save_jpg(im, out)
