"""Generates cheerful, bouncy, royalty-free kids nursery rhyme music tracks.
Features multi-instrument arrangement: xylophone melody, acoustic chord harmony,
walking bassline, and joyful toddler percussion (120 BPM in C Major).
"""
import math
import os
import struct
import subprocess
import wave

MUSIC_DIR = "music"


def generate_nursery_melody(path, duration_sec=64.0):
    """Procedurally synthesizes a cheerful 120 BPM nursery rhyme melody in 44100Hz stereo."""
    rate = 44100
    bpm = 120.0
    beat_sec = 60.0 / bpm  # 0.5 sec per beat
    total_samples = int(rate * duration_sec)

    # Chords progression (4 beats each): C, G, Am, F, C, G, F, C
    chords = [
        [261.63, 329.63, 392.00],  # C major (C4, E4, G4)
        [196.00, 246.94, 293.66],  # G major (G3, B3, D4)
        [220.00, 261.63, 329.63],  # A minor (A3, C4, E4)
        [174.61, 220.00, 261.63],  # F major (F3, A3, C4)
        [261.63, 329.63, 392.00],  # C major
        [196.00, 246.94, 293.66],  # G major
        [174.61, 220.00, 261.63],  # F major
        [261.63, 329.63, 392.00],  # C major
    ]

    # Melody notes (pentatonic cheerful tune)
    melody_notes = [
        523.25, 523.25, 587.33, 659.25,  # C5, C5, D5, E5
        659.25, 587.33, 523.25, 440.00,  # E5, D5, C5, A4
        392.00, 440.00, 523.25, 523.25,  # G4, A4, C5, C5
        587.33, 587.33, 659.25, 523.25,  # D5, D5, E5, C5
        523.25, 659.25, 783.99, 783.99,  # C5, E5, G5, G5
        880.00, 783.99, 659.25, 523.25,  # A5, G5, E5, C5
        587.33, 659.25, 523.25, 392.00,  # D5, E5, C5, G4
        523.25, 587.33, 523.25, 523.25,  # C5, D5, C5, C5
    ]

    left_channel = [0.0] * total_samples
    right_channel = [0.0] * total_samples

    # 1. Acoustic Chords (Warm pad/piano harmony)
    for sample_idx in range(total_samples):
        t = sample_idx / rate
        beat_idx = int(t / (beat_sec * 4)) % len(chords)
        chord_freqs = chords[beat_idx]
        beat_in_chord = (t % (beat_sec * 4)) / beat_sec

        # Gentle envelope per chord strike
        strum_env = math.exp(-0.8 * (beat_in_chord % 1.0))

        chord_val = 0.0
        for f in chord_freqs:
            chord_val += math.sin(2 * math.pi * f * t) * 0.12
            # Rich warm overtone
            chord_val += math.sin(4 * math.pi * f * t) * 0.04

        left_channel[sample_idx] += chord_val * strum_env
        right_channel[sample_idx] += chord_val * strum_env

    # 2. Bouncy Toddler Bassline (pizzicato bass on beats 1 & 3)
    for sample_idx in range(total_samples):
        t = sample_idx / rate
        beat = (t / beat_sec) % 32
        chord_idx = int(beat // 4) % len(chords)
        root_freq = chords[chord_idx][0] / 2.0  # One octave down

        beat_fraction = beat % 2.0
        if beat_fraction < 1.0:
            env = math.exp(-4.5 * beat_fraction)
            bass_val = (
                math.sin(2 * math.pi * root_freq * t) * 0.35 +
                math.sin(4 * math.pi * root_freq * t) * 0.15
            ) * env
            left_channel[sample_idx] += bass_val
            right_channel[sample_idx] += bass_val

    # 3. Bright Xylophone / Bell Melody
    for sample_idx in range(total_samples):
        t = sample_idx / rate
        note_idx = int(t / beat_sec) % len(melody_notes)
        freq = melody_notes[note_idx]
        time_in_note = (t % beat_sec)

        # Xylophone fast decay envelope
        env = math.exp(-5.0 * time_in_note)
        # Bell harmonics (fundamental + 3rd harmonic + subtle chime)
        xylo_val = (
            math.sin(2 * math.pi * freq * t) * 0.40 +
            math.sin(2 * math.pi * freq * 2.0 * t) * 0.18 +
            math.sin(2 * math.pi * freq * 3.0 * t) * 0.08
        ) * env

        # Slight stereo panning for sweetness
        left_channel[sample_idx] += xylo_val * 0.85
        right_channel[sample_idx] += xylo_val * 1.15

    # 4. Soft Shaker / Toddler Percussion (every half beat)
    import random
    rnd = random.Random(42)
    for sample_idx in range(total_samples):
        t = sample_idx / rate
        sub_beat = (t % (beat_sec / 2)) / (beat_sec / 2)
        shaker_env = math.exp(-18 * sub_beat)
        noise = (rnd.random() * 2 - 1) * shaker_env * 0.05
        left_channel[sample_idx] += noise
        right_channel[sample_idx] += noise

    # Write 16-bit stereo WAV
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        raw = bytearray()
        for i in range(total_samples):
            l_val = max(-0.95, min(0.95, left_channel[i]))
            r_val = max(-0.95, min(0.95, right_channel[i]))
            raw += struct.pack("<hh", int(l_val * 32767), int(r_val * 32767))
        wf.writeframes(raw)


def ensure_nursery_music():
    """Ensure high-quality nursery rhyme music files exist in music/."""
    os.makedirs(MUSIC_DIR, exist_ok=True)
    wav_path = os.path.join(MUSIC_DIR, "cheerful_nursery_rhyme.wav")
    mp3_path = os.path.join(MUSIC_DIR, "cheerful_nursery_rhyme.mp3")

    if not os.path.exists(mp3_path) and not os.path.exists(wav_path):
        print("[music] Generating cheerful nursery melody track...")
        generate_nursery_melody(wav_path, duration_sec=64.0)
        # Convert to MP3 if ffmpeg is available
        p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path, "-b:a", "192k", mp3_path])
        if p.returncode == 0 and os.path.exists(mp3_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass


if __name__ == "__main__":
    ensure_nursery_music()

