#!/usr/bin/env python3
"""Hafte me ek baar: (1) tumhare channel ke video ka haal, (2) kids-rhymes me kya chal raha hai,
(3) agle hafte ke 7 naye ORIGINAL idea -> state.ideas me jaate hain (daily pipeline unhe use karta hai).
Sirf API key se padhta hai (upload nahi), isliye YouTube audit ki zaroorat nahi."""
import datetime as dt
import json
import os
import sys

import requests

import delivery
import providers
import state as S

API = "https://www.googleapis.com/youtube/v3"


def yt(path, **params):
    params["key"] = os.environ["YT_API_KEY"]
    r = requests.get(f"{API}/{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def video_rows(ids):
    rows = []
    for i in range(0, len(ids), 50):
        data = yt("videos", part="snippet,statistics", id=",".join(ids[i:i + 50]))
        for it in data.get("items", []):
            st = it.get("statistics", {})
            rows.append({"title": it["snippet"]["title"], "published": it["snippet"]["publishedAt"][:10],
                         "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0))})
    return rows


def my_videos(channel_id):
    ch = yt("channels", part="contentDetails", id=channel_id)
    up = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt("playlistItems", part="contentDetails", playlistId=up, maxResults=30)["items"]
    return video_rows([x["contentDetails"]["videoId"] for x in items])


def trending(queries):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
    ids = []
    for q in queries:
        try:
            res = yt("search", part="snippet", type="video", q=q, order="viewCount", publishedAfter=since,
                     regionCode="IN", maxResults=8)
            ids += [x["id"]["videoId"] for x in res.get("items", [])]
        except Exception as e:
            providers.log("[trend] search fail:", q, e)
    rows = video_rows(list(dict.fromkeys(ids)))
    return sorted(rows, key=lambda r: -r["views"])[:15]


def main():
    cfg = json.load(open("config.json", encoding="utf-8"))
    st = S.load()
    mine, trend = [], []
    if os.getenv("YT_API_KEY"):
        if os.getenv("YT_CHANNEL_ID"):
            try:
                mine = my_videos(os.environ["YT_CHANNEL_ID"])
            except Exception as e:
                providers.log("[weekly] apne video nahi mile:", e)
        try:
            trend = trending(cfg["trend_queries"])
        except Exception as e:
            providers.log("[weekly] trend nahi mila:", e)
    fb = ""
    if os.path.exists("feedback.txt"):
        fb = "\n".join(l for l in open("feedback.txt", encoding="utf-8").read().splitlines() if l.strip() and not l.startswith("#"))
    prompt = f"""You are a YouTube strategist for a kids nursery-rhyme channel "{cfg['channel_name']}" (Hindi+English, ages 2-5).
OUR RECENT VIDEOS (title, views, likes): {json.dumps(mine, ensure_ascii=False)[:3500]}
WHAT IS GETTING VIEWS IN THE NICHE LATELY (titles, views; use ONLY as a signal of which themes work. Never copy a title or song): {json.dumps(trend, ensure_ascii=False)[:3500]}
CREATOR NOTES (CTR / watch-time observations from YouTube Studio): {fb or '(none)'}
ALREADY MADE (do not repeat): {json.dumps(st['used_titles'][-40:], ensure_ascii=False)}

Task: write a short weekly report in simple Hinglish (Roman script), then propose 7 NEW ORIGINAL song ideas for next week.
Ideas must be fresh themes (not copies of any existing song/show), kid-safe, and mixed formats (counting, animals, habits, story, colors, action, lullaby).
Return ONLY JSON: {{"report": "6-10 short lines: what worked, what did not, what to try", "ideas": [{{"topic": "...", "format": "...", "why": "..."}}]}}"""
    data, who = providers.simple_text(prompt, cfg)
    ideas = [i for i in data.get("ideas", []) if isinstance(i, dict) and i.get("topic")][:7]
    st["ideas"] = (st["ideas"] + [{"topic": i["topic"], "format": i.get("format")} for i in ideas])[-21:]
    S.save(st)
    lines = [f"📊 HAFTE KA REPORT ({who})", "", str(data.get("report", "")).strip(), "", "💡 AGLE HAFTE KE IDEAS (automation inhe khud use karega):"]
    lines += [f"{n + 1}. {i['topic']} [{i.get('format', '')}] - {i.get('why', '')}" for n, i in enumerate(ideas)]
    lines += ["", "✍️ Studio me Analytics dekho: CTR aur Average view duration. Jo video achha chala uska kaaran repo ki feedback.txt me 1 line me likh do (jaise: 'counting wale gaane chale, lullaby nahi'). Agle video usi hisaab se banenge."]
    try:
        delivery.send_text("\n".join(lines))
    except Exception as e:
        print("telegram fail:", e)
        print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # weekly report fail ho to daily pipeline pe asar nahi
        delivery.alert(f"Weekly report fail: {e}")
        sys.exit(1)
