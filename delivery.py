"""Delivery: GitHub Release (master video, direct download) + Telegram (preview, thumbnails, title/description)."""
import datetime as dt
import mimetypes
import os
import time

import requests

from providers import log

TG_LIMIT = 48 * 1024 * 1024


def _tg(method, data=None, files=None):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID set nahi hai")
    last = None
    for k in range(3):
        try:
            opened = {name: open(p, "rb") for name, p in (files or {}).items()}
            try:
                r = requests.post(f"https://api.telegram.org/bot{token}/{method}",
                                  data={"chat_id": chat, **(data or {})}, files=opened or None, timeout=300)
            finally:
                for fh in opened.values():
                    fh.close()
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(4 * (k + 1))
    raise RuntimeError(f"telegram {method} fail: {last}")


def send_text(text):
    for i in range(0, len(text), 3900):
        _tg("sendMessage", {"text": text[i:i + 3900], "disable_web_page_preview": "true"})


def alert(text):
    """Alert kabhi crash nahi karta."""
    try:
        send_text("⚠️ " + text)
    except Exception as e:
        log("[alert] telegram nahi gaya:", e)


# ----------------------------------------------------------------- GitHub release
def _gh_headers():
    return {"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN', '')}", "Accept": "application/vnd.github+json"}


def publish_release(tag, title, files):
    """Files ko release assets banata hai; {filename: direct_url} wapas."""
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError("GITHUB_TOKEN / GITHUB_REPOSITORY nahi mila (sirf GitHub Actions me chalta hai)")
    r = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=_gh_headers(), timeout=60,
                      json={"tag_name": tag, "name": title, "body": "auto-generated", "prerelease": True})
    r.raise_for_status()
    rel = r.json()
    upload = rel["upload_url"].split("{")[0]
    urls = {}
    for path in files:
        name = os.path.basename(path)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        for k in range(3):
            try:
                with open(path, "rb") as f:
                    u = requests.post(upload, params={"name": name}, data=f, timeout=900,
                                      headers={**_gh_headers(), "Content-Type": ctype})
                u.raise_for_status()
                urls[name] = u.json()["browser_download_url"]
                break
            except Exception as e:
                log(f"[release] {name} upload fail ({e}) try {k + 1}/3")
                time.sleep(5 * (k + 1))
    return urls


def prune_releases(keep_days):
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or not os.getenv("GITHUB_TOKEN"):
        return
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/releases?per_page=100", headers=_gh_headers(), timeout=60)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=keep_days)
        for rel in r.json():
            if not rel.get("tag_name", "").startswith("v-"):
                continue
            created = dt.datetime.fromisoformat(rel["created_at"].replace("Z", "+00:00"))
            if created < cutoff:
                requests.delete(f"https://api.github.com/repos/{repo}/releases/{rel['id']}", headers=_gh_headers(), timeout=60)
                requests.delete(f"https://api.github.com/repos/{repo}/git/refs/tags/{rel['tag_name']}", headers=_gh_headers(), timeout=60)
    except Exception as e:
        log("[release] purane releases saaf nahi hue:", e)


# ---------------------------------------------------------------------- Telegram
def send_package(v, urls):
    """v: dict (title, meta_text, thumbs, preview). Telegram par sab bhejta hai. Kuch fail ho to baaki chalta rehta hai."""
    ok = False
    for label, path in (("A", v["thumb_a"]), ("B", v["thumb_b"])):
        try:
            _tg("sendPhoto", {"caption": f"Thumbnail {label}"}, {"photo": path})
            ok = True
        except Exception as e:
            log("[tg] thumbnail fail:", e)
    try:
        if os.path.getsize(v["preview"]) <= TG_LIMIT:
            _tg("sendVideo", {"caption": f"Preview: {v['title_en']}", "supports_streaming": "true"}, {"video": v["preview"]})
            ok = True
    except Exception as e:
        log("[tg] preview fail:", e)
    links = "\n".join(f"{n}: {u}" for n, u in urls.items()) or "(release link nahi bana - GitHub run ke Artifacts me files hain)"
    try:
        send_text(v["meta_text"] + "\n\n⬇️ DOWNLOAD LINKS\n" + links)
        ok = True
    except Exception as e:
        log("[tg] text fail:", e)
    return ok
