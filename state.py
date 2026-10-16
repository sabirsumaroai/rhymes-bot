import json
import os
import re

STATE_DIR = "state"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
SCRIPTS_DIR = os.path.join(STATE_DIR, "scripts")

DEFAULT = {"used_titles": [], "used_topics": [], "ideas": [], "missed": 0, "runs": 0,
           "last_run": "", "voiced": [], "counter": 0}


def load():
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    return {**DEFAULT, **data}


def save(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


def slug(text, n=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:n] or "video"


def norm_tokens(title):
    return set(re.findall(r"\w+", title.lower()))


def too_similar(title, used, thr=0.8):
    a = norm_tokens(title)
    for u in used:
        b = norm_tokens(u)
        if a and b and len(a & b) / len(a | b) >= thr:
            return True
    return False
