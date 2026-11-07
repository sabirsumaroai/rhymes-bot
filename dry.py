"""DRY_RUN=1 ke liye nakli (offline) script aur awaaz, taaki poora pipeline bina internet/keys ke test ho sake."""
import random
import subprocess


def fake_script(prompt):
    rnd = random.Random(len(prompt))
    n = rnd.randint(1, 9999)
    if "30-SECOND" in prompt or "Shorts" in prompt:
        scenes = [
            {"text": "अरे! इस जादुई डिब्बे में क्या है?\nLook! What is inside?", "lang": "hi", "chorus": False, "image_prompt": "Chintu looking curious at a glowing magical box"},
            {"text": "Tap tap tap! One, two, three!\nचलो मिलकर देखें!", "lang": "en", "chorus": False, "image_prompt": "Chintu tapping the magic box"},
            {"text": "डिब्बा धीरे-धीरे खुला!\nWho is hiding inside?", "lang": "hi", "chorus": False, "image_prompt": "Box lid opening with shiny sparkles"},
            {"text": "BOING! It's a happy blue bunny!\nछोटा खरगोश कूदा!", "lang": "en", "chorus": False, "image_prompt": "Cute blue bunny hopping out of the box with big smile"},
            {"text": "मीठू तोता भी आया नाचे!\nHop hop hop together!", "lang": "hi", "chorus": False, "image_prompt": "Mithu parrot dancing joyfully with the bunny"},
            {"text": "High five, bunny! You are so sweet!\nसब मिलकर तालियां बजाओ!", "lang": "en", "chorus": False, "image_prompt": "Chintu and bunny giving cute high five"},
            {"text": "खरगोश वापस गया डिब्बे के अंदर!\nWait, don't go away!", "lang": "hi", "chorus": False, "image_prompt": "Bunny winking as it steps back into the box"},
            {"text": "फिर से देखो! डिब्बे में क्या है?\nLook again! What's inside?", "lang": "hi", "chorus": False, "image_prompt": "Box glowing again ready to loop"}
        ]
        return {
            "title_hi": f"जादुई डिब्बा {n}",
            "title_en": f"The Mystery Magic Box {n}",
            "thumb_text_hi": "जादुई डिब्बा",
            "thumb_text_en": "MAGIC BOX!",
            "description": "Watch what happens when Chintu opens the mystery magic box! #Shorts #KidsRhymes #Cartoon",
            "tags": ["kids shorts", "magic box", "chintu cartoon", "toddler rhymes", "hindi rhymes shorts", "funny kids video"],
            "learning": "curiosity and counting",
            "scenes": scenes,
        }

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
