#!/usr/bin/env python3
"""Roz video banane wala pipeline.

  python main.py daily [--count N]     -> naye video banao aur Telegram/Release par bhejo
  python main.py voice                 -> my_voice/ me rakhi apni awaaz ke saath video banao
  python main.py daily --dry           -> bina internet/keys ke pura test (nakli data)
"""
import argparse
import datetime as dt
import glob
import json
import os
import random
import shutil
import sys
import traceback

if "--dry" in sys.argv:
    os.environ["DRY_RUN"] = "1"

import delivery  # noqa: E402
import providers  # noqa: E402
import render  # noqa: E402
import state as S  # noqa: E402
from providers import log  # noqa: E402

DRY = os.getenv("DRY_RUN") == "1"
OUT_ROOT = "out"
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus"}


def load_cfg():
    with open("config.json", encoding="utf-8") as f:
        return json.load(f)


def read_feedback():
    try:
        with open("feedback.txt", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        return "\n".join(lines)[:1500]
    except OSError:
        return ""


# ----------------------------------------------------------------------- script
def build_prompt(cfg, st, topic, fmt):
    chars = "\n".join("- " + c for c in cfg["characters"])
    avoid = "\n".join("- " + t for t in st["used_titles"][-60:]) or "(none yet)"
    fb = read_feedback()
    topic_line = (f"Topic: {topic}" if topic else
                  "Topic: invent a fresh, specific topic yourself that is NOT similar to any title in the avoid list.")
    return f"""You are a gifted children's songwriter for the Indian YouTube channel "{cfg['channel_name']}" (audience: ages 2-5).
Write ONE brand-new, 100% ORIGINAL nursery rhyme / kids song.

HARD RULES
- Completely original lyrics. Never copy, imitate or paraphrase any existing song, rhyme, show, character or channel. No brand names.
- Gentle, positive, safe for toddlers. Nothing scary, violent or sad.
- Recurring ORIGINAL characters you may use:
{chars}
- {topic_line}
- Song format: {fmt}
- Lyrics alternate between simple Hindi (Devanagari script) and simple English. Set "lang" to "hi" or "en" for each scene (the whole scene text must be in that language).
- Scene 1 MUST be the catchiest chorus (chorus=true) so the song starts instantly: NO greeting, NO intro, NO "hello friends".
- 26 to 32 scenes. Each scene = 1-2 short lines (max 12 words per line). Verses are 4 lines (2 scenes). The same 2-line chorus returns after every 2 verses with IDENTICAL text and chorus=true.
- Teach one tiny thing that fits the format (counting, colors, a habit, an animal sound...).
- "image_prompt": English, ONE simple scene for a cute 3D cartoon picture, name the characters by look (not copyrighted names), describe action and place. Different for every scene. No text, letters or logos in the picture.
- "thumb_text_hi" / "thumb_text_en": 2-4 punchy words each for a YouTube thumbnail.
- "description": 2 short friendly sentences in Hinglish for parents (what kids learn).
- "tags": 12 relevant search tags (Hindi and English).

CREATOR NOTES (follow these, they come from what worked / did not work before):
{fb or '(none)'}

AVOID titles similar to:
{avoid}

Return ONLY valid JSON, no markdown:
{{"title_hi": "...", "title_en": "...", "thumb_text_hi": "...", "thumb_text_en": "...", "description": "...", "tags": ["..."],
 "learning": "...", "scenes": [{{"text": "line1\\nline2", "lang": "hi", "chorus": true, "image_prompt": "..."}}]}}"""


def make_validator(cfg, st):
    blocked = [b.lower() for b in cfg["blocked_terms"]]

    def validate(d):
        for k in ("title_hi", "title_en", "description", "tags", "scenes"):
            if not d.get(k):
                raise ValueError(f"'{k}' missing")
        sc = d["scenes"]
        if not isinstance(sc, list) or not 12 <= len(sc) <= 60:
            raise ValueError(f"scenes ki ginti theek nahi ({len(sc) if isinstance(sc, list) else '?'})")
        for s in sc:
            if not str(s.get("text", "")).strip() or s.get("lang") not in ("hi", "en") or not str(s.get("image_prompt", "")).strip():
                raise ValueError("kisi scene me text/lang/image_prompt kharab hai")
            s["text"] = str(s["text"]).strip()
            s["chorus"] = bool(s.get("chorus"))
        blob = json.dumps(d, ensure_ascii=False).lower()
        for b in blocked:
            if b in blob:
                raise ValueError(f"blocked term mila: {b}")
        if S.too_similar(d["title_en"], st["used_titles"]):
            raise ValueError("title purane jaisa hai")
        d["tags"] = [str(t) for t in d["tags"]][:20]
        d["thumb_text_hi"] = d.get("thumb_text_hi") or d["title_hi"]
        d["thumb_text_en"] = d.get("thumb_text_en") or d["title_en"]

    return validate


def pick_plan(cfg, st):
    idea = st["ideas"][0] if st["ideas"] else None
    if idea:
        topic, fmt = idea.get("topic"), idea.get("format")
    else:
        unused = [t for t in cfg["topics"] if t not in st["used_topics"]]
        topic, fmt = (random.choice(unused) if unused else None), None
    fmt = fmt or cfg["formats"][st["counter"] % len(cfg["formats"])]
    return idea, topic, fmt


def fit_scenes(scenes, durs, min_s, max_s):
    """Rhyme ko 6-8 minute me fit karo: chorus dohrao (kam ho to) / aakhir se hatao (zyada ho to)."""
    seq = list(range(len(scenes)))
    total = sum(durs)
    chorus = [i for i, s in enumerate(scenes) if s["chorus"]] or list(range(min(4, len(scenes))))
    k = 0
    while total < min_s and k < 60:
        i = chorus[k % len(chorus)]
        seq.append(i)
        total += durs[i]
        k += 1
    while total > max_s and len(seq) > 10:
        total -= durs[seq.pop()]
    return seq, total


# ------------------------------------------------------------------- production
def full_image_prompt(cfg, scene):
    chars = "; ".join(c.split(":")[0] + ": " + c.split(":", 1)[-1].strip() for c in cfg["characters"])
    return f"{scene['image_prompt']}. Characters (keep same look): {chars}. Style: {cfg['style_prompt']}"[:900]


def pick_music():
    files = [f for ext in ("mp3", "wav", "m4a", "ogg") for f in glob.glob(f"music/*.{ext}")]
    return random.choice(files) if files else None


def build_meta(cfg, script, vid, notes, short_title):
    footer = (f"Original rhymes and visuals created with AI tools. Subscribe to {cfg['channel_name']} "
              "for new kids rhymes!")
    tagline = " ".join("#" + "".join(ch for ch in t.title() if ch.isalnum()) for t in script["tags"][:4] if t)
    desc = f"{script['description'].strip()}\n\n{footer}\n\n{tagline}".strip()
    tags, total = [], 0
    for t in script["tags"]:
        if total + len(t) + 1 > 450:
            break
        tags.append(t)
        total += len(t) + 1
    t1 = f"{script['title_hi']} | {script['title_en']}"[:98]
    lyrics = "\n\n".join(s["text"] for s in script["scenes"])
    text = (f"🎬 NAYA VIDEO READY: {vid}\n"
            + ("\n".join("⚠️ " + n for n in notes) + "\n" if notes else "")
            + f"\nTITLE (option 1): {t1}\nTITLE (option 2): {script['title_en'][:98]}\nTITLE (option 3): {script['title_hi'][:98]}\n"
              f"\nSHORT TITLE: {short_title}\n\nDESCRIPTION:\n{desc}\n\nTAGS: {', '.join(tags)}\n"
              "\n✅ UPLOAD CHECKLIST\n1. Studio me 'Made for kids' = Haan (Yes) chuno\n2. Thumbnail A ya B lagao\n"
              "3. Title/description/tags paste karo\n4. Short alag se upload karo (Shorts)\n"
              "5. Apni awaaz lagani ho to lyrics padh ke record karo, my_voice/ me upload karo\n"
              f"\n📝 LYRICS\n{lyrics}")
    return text, desc, t1


def make_video(cfg, st, script, vid_id, human_audio=None, notes=None):
    notes = list(notes or [])
    out = os.path.join(OUT_ROOT, vid_id)
    work = os.path.join("work", vid_id)
    for d in (out, work):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    scenes = script["scenes"]
    min_s, max_s = cfg["length"]["min_minutes"] * 60, cfg["length"]["max_minutes"] * 60

    # 1) awaaz
    wavs = {}
    if human_audio:
        total = render.duration(human_audio)
        if total < 30:
            raise RuntimeError("recording bahut chhoti hai")
        w = [max(8, len(s["text"])) for s in scenes]
        durs, t0 = [], 0.0
        for i, s in enumerate(scenes):
            d = total * w[i] / sum(w)
            p = os.path.join(work, f"voice_{i:03d}.wav")
            render.ff("-ss", f"{t0:.3f}", "-t", f"{d:.3f}", "-i", human_audio, "-ar", "44100", "-ac", "1", p)
            wavs[i] = p
            durs.append(d)
            t0 += d
        seq, total_s = list(range(len(scenes))), total
    else:
        cache, durs, srcs = {}, [], set()
        for i, s in enumerate(scenes):
            key = (s["text"], s["lang"])
            if key not in cache:
                p = os.path.join(work, f"tts_{len(cache):03d}.wav")
                d, src = providers.synthesize(s["text"], s["lang"], p, cfg)
                cache[key] = (p, d)
                srcs.add(src)
            wavs[i], d = cache[key]
            durs.append(d)
        log(f"[tts] sources: {sorted(srcs)}")
        if srcs and srcs <= {"espeak"}:
            notes.append("Awaaz basic fallback (espeak) se bani - quality kam hai")
        seq, total_s = fit_scenes(scenes, durs, min_s, max_s)
        if total_s < min_s - 60:
            raise RuntimeError(f"video bahut chhota ban raha hai ({total_s:.0f}s)")

    # 2) images (sirf jo scenes use ho rahe hain)
    imgs, sources = {}, []
    for n, i in enumerate(sorted(set(seq))):
        imgs[i], src = providers.get_image(full_image_prompt(cfg, scenes[i]), cfg["image_seed"], i, scenes[i]["text"], cfg, work)
        sources.append(src)
        log(f"[img] {n + 1}/{len(set(seq))} scene {i} via {src}")
    providers.prune_cache(cfg)
    art = sources.count("pillow-art") + sources.count("old-cache")
    if sources and art / len(sources) > 0.4:
        notes.append(f"{art}/{len(sources)} images fallback se bani (image service chal nahi rahi thi) - quality kam hai, dekh ke upload karo")

    # 3) clips -> master
    caps = {}
    for i in set(seq):
        caps[i] = os.path.join(work, f"cap_{i:03d}.png")
        render.caption_png(scenes[i]["text"], caps[i])
    clips, cdurs, made = [], [], {}
    for i in seq:  # dohraye hue scene ka clip ek hi baar banta hai (time bachta hai)
        if i not in made:
            made[i] = os.path.join(work, f"clip_{i:03d}.mp4")
            render.scene_clip(imgs[i], wavs[i], caps[i], durs[i], i, made[i])
            log(f"[clip] {len(made)}/{len(set(seq))}")
        clips.append(made[i])
        cdurs.append(durs[i])
    raw = os.path.join(work, "master_raw.mp4")
    render.concat(clips, raw, work)
    master = os.path.join(out, "master.mp4")
    music = None if human_audio else pick_music()
    if music:
        render.add_music(raw, music, master)
    else:
        shutil.copy(raw, master)

    # 4) short, thumbnails, preview
    short = os.path.join(out, "short.mp4")
    short_len = render.make_short(clips, cdurs, short, work)
    uniq = sorted(set(seq))
    render.thumbnail(imgs[seq[0]], script["thumb_text_hi"], os.path.join(out, "thumb_a.jpg"), "A")
    render.thumbnail(imgs[uniq[len(uniq) // 2]], script["thumb_text_en"], os.path.join(out, "thumb_b.jpg"), "B")
    preview = os.path.join(out, "preview.mp4")
    render.make_preview(master, preview)

    # 5) quality check
    dur = render.duration(master)
    if abs(dur - total_s) > 4 or os.path.getsize(master) < 500_000 or short_len < 10:
        raise RuntimeError(f"QC fail: duration {dur:.1f}s (expected {total_s:.1f}s)")
    log(f"[qc] ok: {dur / 60:.1f} min, master {os.path.getsize(master) / 1e6:.1f}MB, short {short_len:.0f}s")

    short_title = f"{script['title_en']} #Shorts"[:98]
    meta_text, desc, t1 = build_meta(cfg, script, vid_id, notes, short_title)
    with open(os.path.join(out, "meta.txt"), "w", encoding="utf-8") as f:
        f.write(meta_text)
    return {"id": vid_id, "title_en": script["title_en"], "meta_text": meta_text, "dir": out,
            "master": master, "short": short, "preview": preview,
            "thumb_a": os.path.join(out, "thumb_a.jpg"), "thumb_b": os.path.join(out, "thumb_b.jpg"),
            "work": work}


def deliver(cfg, v):
    if DRY:
        log(f"[dry] delivery skip. Files: {v['dir']}")
        return
    urls = {}
    try:
        urls = delivery.publish_release("v-" + v["id"], v["title_en"],
                                        [v["master"], v["short"], v["thumb_a"], v["thumb_b"]])
    except Exception as e:
        log("[release] fail:", e)
    ok = delivery.send_package(v, urls)
    if not urls and not ok:
        raise RuntimeError("na release bana, na Telegram gaya")
    delivery.prune_releases(cfg["release_keep_days"])


# --------------------------------------------------------------------- commands
def check_hindi_rendering():
    """Devanagari ke liye Pillow me raqm chahiye. Na ho to chetavni (video phir bhi banta hai)."""
    try:
        from PIL import features
        if not features.check("raqm"):
            log("[warn] Pillow me raqm nahi hai - Hindi text toota hua dikh sakta hai")
            if not DRY:
                delivery.alert("Hindi text sahi se nahi dikhega (Pillow raqm missing). Workflow me libraqm0 install hona chahiye.")
    except Exception:
        pass


def cmd_daily(cfg, count_override=None):
    check_hindi_rendering()
    st = S.load()
    want = count_override or (cfg["videos_per_run"] + min(st["missed"], cfg["max_catchup"]))
    log(f"[daily] aaj {want} video banane hain (missed={st['missed']})")
    produced, errors = 0, []
    for n in range(want):
        for attempt in range(2):
            vid = None
            try:
                idea, topic, fmt = pick_plan(cfg, st)
                prompt = build_prompt(cfg, st, topic, fmt)
                script, who = providers.generate_script(prompt, cfg, make_validator(cfg, st))
                vid = f"{dt.date.today():%Y%m%d}-{st['counter'] + 1:03d}-{S.slug(script['title_en'], 28)}"
                log(f"[script] {script['title_en']} via {who} | topic={topic} | format={fmt}")
                with open(os.path.join(S.SCRIPTS_DIR, vid + ".json"), "w", encoding="utf-8") as f:
                    json.dump({"id": vid, "topic": topic, "format": fmt, **script}, f, ensure_ascii=False, indent=1)
                v = make_video(cfg, st, script, vid)
                deliver(cfg, v)
                st["used_titles"].append(script["title_en"])
                if topic:
                    st["used_topics"].append(topic)
                if idea in st["ideas"]:
                    st["ideas"].remove(idea)
                st["counter"] += 1
                produced += 1
                S.save(st)
                shutil.rmtree(v["work"], ignore_errors=True)
                break
            except Exception as e:  # ek video fail hone se baaki nahi rukte
                traceback.print_exc()
                errors.append(f"{type(e).__name__}: {str(e)[:200]}")
                if vid:
                    try:
                        os.remove(os.path.join(S.SCRIPTS_DIR, vid + ".json"))
                    except OSError:
                        pass
    if not count_override:
        st["missed"] = min(14, max(0, st["missed"] + cfg["videos_per_run"] - produced))
    st["runs"] += 1
    st["last_run"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    S.save(st)
    if produced < want and not DRY:
        delivery.alert(f"{want} me se {produced} video bane. Aakhri errors: {' | '.join(errors[-3:])}\n"
                       f"Agli baar apne aap {min(st['missed'], cfg['max_catchup'])} extra bana dunga.")
    log(f"[daily] done: {produced}/{want}")
    if produced == 0:
        sys.exit(1)


def cmd_voice(cfg, vdir="my_voice"):
    st = S.load()
    done = 0
    for path in sorted(glob.glob(os.path.join(vdir, "*"))):
        stem, ext = os.path.splitext(os.path.basename(path))
        if ext.lower() not in AUDIO_EXT or stem in st["voiced"]:
            continue
        sp = os.path.join(S.SCRIPTS_DIR, stem + ".json")
        if not os.path.exists(sp):
            delivery.alert(f"my_voice/{os.path.basename(path)}: iske naam ki script nahi mili. Naam bilkul video ID jaisa rakho (Telegram message me 'NAYA VIDEO READY: <ID>').")
            continue
        try:
            with open(sp, encoding="utf-8") as f:
                script = json.load(f)
            v = make_video(cfg, st, script, stem + "-voice", human_audio=path)
            deliver(cfg, v)
            st["voiced"].append(stem)
            S.save(st)
            shutil.rmtree(v["work"], ignore_errors=True)
            done += 1
        except Exception as e:
            traceback.print_exc()
            delivery.alert(f"Apni awaaz wala video fail: {stem}: {e}")
    log(f"[voice] {done} video bane")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["daily", "voice"])
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cfg = load_cfg()
    count = a.count if a.count and a.count > 0 else None
    # count=1 normal din ka hi matlab hai; bada count (7 jaisa) tabhi override maano
    if count == 1:
        count = None
    if a.cmd == "daily":
        cmd_daily(cfg, count)
    else:
        cmd_voice(cfg)


if __name__ == "__main__":
    main()
