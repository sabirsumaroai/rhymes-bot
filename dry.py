"""DRY_RUN=1 ke liye nakli (offline) script aur awaaz, taaki poora pipeline bina internet/keys ke test ho sake."""
import random
import subprocess


def fake_script(prompt):
    rnd = random.Random(len(prompt))
    n = rnd.randint(1, 9999)
    chorus = {"text": "हम सब मिलकर गाएँ\nLa la la, sing along!", "lang": "hi"}
    scenes = []
    for v in range(6):
        scenes.append({**chorus, "chorus": True,
                       "image_prompt": f"Chintu the baby elephant dancing happily in a garden, scene {v}a"})
        for line in range(4):
            lang = "hi" if v % 2 == 0 else "en"
            txt = (f"छोटा हाथी चिंटू नाचे\nगिनती {v}-{line} गाए" if lang == "hi"
                   else f"Little Chintu jumps up high\nCounting {v}-{line} to the sky")
            scenes.append({"text": txt, "lang": lang, "chorus": False,
                           "image_prompt": f"Mithu the parrot and Chintu playing, scene {v}-{line}"})
    return {
        "title_hi": f"चिंटू का मज़ेदार गाना {n}",
        "title_en": f"Chintu's Happy Counting Song {n}",
        "thumb_text_hi": "चिंटू का गाना",
        "thumb_text_en": "Chintu Sings!",
        "description": "Ek pyaara original rhyme bachho ke liye.",
        "tags": ["hindi rhymes", "kids songs", "nursery rhymes hindi", "toddler songs"],
        "learning": "counting",
        "scenes": scenes,
    }


def fake_tts(text, out_wav):
    d = max(2.0, 0.22 * len(text) + 1.5)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=330:sample_rate=44100:duration={d:.2f}", "-ac", "1", out_wav],
                   check=True, capture_output=True)
    return d + 0.45, "dry-tone"
