#!/usr/bin/env python3
"""Delivers a specific GitHub release video directly to Telegram."""
import os
import sys
import time
import requests

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
GH_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO = os.getenv("GITHUB_REPOSITORY", "sabirsumaroai/rhymes-bot")

if not TG_TOKEN or not TG_CHAT:
    print("Error: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing")
    sys.exit(1)

tag = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "latest" else None

headers = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"} if GH_TOKEN else {}

if tag:
    url = f"https://api.github.com/repos/{REPO}/releases/tags/{tag}"
else:
    url = f"https://api.github.com/repos/{REPO}/releases?per_page=1"

r = requests.get(url, headers=headers, timeout=30)
r.raise_for_status()
rel = r.json()[0] if isinstance(r.json(), list) else r.json()

print(f"Delivering release: {rel.get('tag_name')} - {rel.get('name')}")

# Download video asset and thumbnail
os.makedirs("dl", exist_ok=True)
video_path = None
thumb_path = None

for a in rel.get("assets", []):
    name = a["name"]
    dl_url = a["browser_download_url"]
    out_p = os.path.join("dl", name)
    print(f"Downloading {name}...")
    res = requests.get(dl_url, timeout=120)
    with open(out_p, "wb") as f:
        f.write(res.content)
    if name in ("short.mp4", "master.mp4", "preview.mp4") and not video_path:
        video_path = out_p
    elif name.startswith("thumb_a") and not thumb_path:
        thumb_path = out_p

# Send to Telegram
if thumb_path and os.path.exists(thumb_path):
    print("Sending thumbnail to Telegram...")
    with open(thumb_path, "rb") as fh:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                      data={"chat_id": TG_CHAT, "caption": f"🌟 Thumbnail: {rel.get('name')}"},
                      files={"photo": fh}, timeout=60)

if video_path and os.path.exists(video_path):
    print("Sending video to Telegram...")
    caption = f"🎬 30-Second Trial Short: {rel.get('name')}\n\n✨ Vertical 9:16 Format | Pure Original Rhyme"
    with open(video_path, "rb") as fh:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
                      data={"chat_id": TG_CHAT, "caption": caption, "supports_streaming": "true"},
                      files={"video": fh}, timeout=300)

print("Telegram delivery complete!")
