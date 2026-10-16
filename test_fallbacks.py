"""Fallback chains ka test (offline, nakli responses). Chalane ke liye: python -m unittest discover -s tests -v"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.pop("DRY_RUN", None)

import main  # noqa: E402
import providers  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
GOOD = {"title_en": "t", "scenes": [{"text": "a"}] * 3}


class Resp:
    def __init__(self, code, payload=None, text=""):
        self.status_code, self._p, self.text = code, payload, text

    def json(self):
        return self._p


class LLMChain(unittest.TestCase):
    def test_gemini_limit_then_groq_works(self):
        calls = []

        def fake_post(url, **kw):
            calls.append(url)
            if "flash-lite:generate" in url and "3.1" not in url:
                return Resp(429)                                   # limit
            if "2.5-flash:generate" in url:
                return Resp(404)                                   # model hat gaya
            if "generativelanguage" in url:
                return Resp(200, {"candidates": [{"content": {"parts": [{"text": "not json at all"}]}}]})
            return Resp(200, {"choices": [{"message": {"content": "```json\n" + json.dumps(GOOD) + "\n```"}}]})

        env = {"GEMINI_API_KEY": "x", "GROQ_API_KEY": "y"}
        with mock.patch.dict(os.environ, env), mock.patch("providers.requests.post", fake_post), \
                mock.patch("providers.time.sleep"):
            data, who = providers.generate_script("p", CFG, lambda d: d["scenes"])
        self.assertEqual(who, "groq")
        self.assertEqual(data["title_en"], "t")
        self.assertTrue(any("3.1-flash-lite" in c for c in calls))   # saare Gemini models try hue

    def test_all_fail_raises(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "x"}, clear=False), \
                mock.patch("providers.requests.post", lambda *a, **k: Resp(429)), mock.patch("providers.time.sleep"):
            for k in ("GROQ_API_KEY", "OPENROUTER_API_KEY"):
                os.environ.pop(k, None)
            with self.assertRaises(providers.ProviderError):
                providers.generate_script("p", CFG, lambda d: None)


class ImageChain(unittest.TestCase):
    def setUp(self):
        self.w = tempfile.mkdtemp()
        self.cache = tempfile.mkdtemp()
        self.p = mock.patch.object(providers, "CACHE_DIR", self.cache)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        shutil.rmtree(self.w, ignore_errors=True)
        shutil.rmtree(self.cache, ignore_errors=True)

    def test_pollinations_down_uses_pillow_art(self):
        with mock.patch.object(providers, "_pollinations", side_effect=providers.ProviderError("down")), \
                mock.patch.object(providers, "_throttle"), mock.patch("providers.time.sleep"):
            path, src = providers.get_image("prompt", 1, 0, "text", CFG, self.w)
        self.assertEqual(src, "pillow-art")
        self.assertTrue(providers._valid_image(path))

    def test_old_cache_used_when_down(self):
        providers.fallback_art(os.path.join(self.cache, "old.jpg"), 3)
        with mock.patch.object(providers, "_pollinations", side_effect=providers.ProviderError("down")), \
                mock.patch.object(providers, "_throttle"), mock.patch("providers.time.sleep"):
            path, src = providers.get_image("prompt2", 1, 0, "text", CFG, self.w)
        self.assertEqual(src, "old-cache")

    def test_success_is_cached(self):
        def ok(prompt, seed, out):
            providers.fallback_art(out, 5)
        with mock.patch.object(providers, "_pollinations", side_effect=ok), mock.patch.object(providers, "_throttle"):
            _, s1 = providers.get_image("same", 1, 0, "t", CFG, self.w)
            _, s2 = providers.get_image("same", 1, 1, "t", CFG, self.w)
        self.assertEqual((s1, s2), ("pollinations", "cache"))


def _sine(path, secs=3):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=300:duration={secs}", "-f", "wav", path], check=True)


class TTSChain(unittest.TestCase):
    def test_edge_down_gtts_works(self):
        w = tempfile.mkdtemp()
        with mock.patch.object(providers, "_tts_edge", side_effect=RuntimeError("edge band")), \
                mock.patch.object(providers, "_tts_gtts", side_effect=lambda t, l, out, tld: _sine(out + "", 3)), \
                mock.patch("providers.time.sleep"):
            # gtts fake ko .raw file chahiye, isliye out = tmp path
            d, src = providers.synthesize("namaste bachon", "hi", os.path.join(w, "a.wav"), CFG)
        self.assertEqual(src, "gtts")
        self.assertGreater(d, 2.5)

    def test_all_down_raises(self):
        w = tempfile.mkdtemp()
        with mock.patch.object(providers, "_tts_edge", side_effect=RuntimeError("x")), \
                mock.patch.object(providers, "_tts_gtts", side_effect=RuntimeError("y")), \
                mock.patch.object(providers, "_tts_espeak", side_effect=RuntimeError("z")), \
                mock.patch("providers.time.sleep"):
            with self.assertRaises(providers.ProviderError):
                providers.synthesize("x", "en", os.path.join(w, "a.wav"), CFG)


class ScriptRules(unittest.TestCase):
    def setUp(self):
        from dry import fake_script
        self.script = fake_script("seed")
        self.st = {"used_titles": []}

    def test_blocked_term_rejected(self):
        self.script["scenes"][3]["text"] = "Let us sing Baby Shark today"
        with self.assertRaises(ValueError):
            main.make_validator(CFG, self.st)(self.script)

    def test_repeat_title_rejected(self):
        self.st["used_titles"] = [self.script["title_en"]]
        with self.assertRaises(ValueError):
            main.make_validator(CFG, self.st)(self.script)

    def test_good_script_passes(self):
        main.make_validator(CFG, self.st)(self.script)

    def test_fit_scenes_extends_and_trims(self):
        scenes = [{"chorus": i % 5 == 0} for i in range(20)]
        seq, tot = main.fit_scenes(scenes, [10.0] * 20, 360, 480)
        self.assertTrue(360 <= tot <= 480, tot)
        seq, tot = main.fit_scenes(scenes, [40.0] * 20, 360, 480)
        self.assertLessEqual(tot, 480)


if __name__ == "__main__":
    unittest.main()
