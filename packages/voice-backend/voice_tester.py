#!/usr/bin/env python3
"""
Interactive Kokoro voice tester.
Press number keys to hear different voices with the same phrase.
"""

import os
import subprocess
import tempfile
from pathlib import Path

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

print("Loading Kokoro model (one-time, ~2s)...")
from kokoro import KPipeline
import numpy as np
import scipy.io.wavfile as wavfile

# Load model once - voices switch instantly after this
pipe = KPipeline(lang_code='a', device='cuda', repo_id='hexgrad/Kokoro-82M')
print("Model loaded! Voice switching is now instant.\n")

# Test voices organized by category
VOICES = [
    # American Female (top picks)
    ("af_heart", "A", "American Female - BEST"),
    ("af_bella", "A-", "American Female"),
    ("af_nicole", "B", "American Female"),
    ("af_sky", "B", "American Female"),
    ("af_sarah", "C+", "American Female"),
    ("af_nova", "C+", "American Female"),
    ("af_jessica", "C", "American Female"),
    ("af_river", "C", "American Female"),
    ("af_alloy", "C", "American Female"),
    # British Female
    ("bf_emma", "B-", "British Female"),
    ("bf_isabella", "B-", "British Female"),
    ("bf_alice", "C", "British Female"),
    ("bf_lily", "C", "British Female"),
    # British Male
    ("bm_george", "C+", "British Male"),
    ("bm_lewis", "C+", "British Male"),
    ("bm_daniel", "C", "British Male"),
    ("bm_fable", "C", "British Male"),
    # American Male (am_michael = your current pick!)
    ("am_michael", "C+", "American Male - YOUR PICK"),
    ("am_adam", "B-", "American Male"),
    ("am_fenrir", "C+", "American Male"),
    ("am_puck", "C+", "American Male"),
    ("am_echo", "C", "American Male"),
    ("am_eric", "C", "American Male"),
    ("am_liam", "C", "American Male"),
]

TEST_PHRASES = [
    "Hello Commander. I'm IRIS, your AI companion for Star Atlas.",
    "Your fleet is currently stationed in the MRZ sector.",
    "I've detected some interesting market opportunities for you.",
    "Would you like me to analyze your resource production?",
]

current_phrase_idx = 0

def play_voice(voice_id: str, text: str):
    """Generate and play audio for a voice."""
    # Generate audio
    gen = pipe(text, voice=voice_id)
    audio_chunks = []
    for _, _, audio in gen:
        audio_chunks.append(audio)

    if not audio_chunks:
        print("  No audio generated!")
        return

    full_audio = np.concatenate(audio_chunks)

    # Save to temp file and play
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wavfile.write(f.name, 24000, (full_audio * 32767).astype(np.int16))
        # Play with aplay (suppress output)
        subprocess.run(['aplay', '-q', f.name], check=True)
        os.unlink(f.name)

def show_menu():
    print("\n" + "="*70)
    print("KOKORO VOICE TESTER - Enter number to hear voice")
    print("="*70)

    # Group by category
    categories = {}
    for i, (vid, grade, desc) in enumerate(VOICES):
        cat = desc.split(" - ")[0] if " - " in desc else desc
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((i+1, vid, grade, desc))

    for cat, voices in categories.items():
        print(f"\n  {cat}:")
        for num, vid, grade, desc in voices:
            marker = " ***" if "YOUR PICK" in desc or "BEST" in desc else ""
            print(f"    [{num:2}] {vid:15} ({grade}){marker}")

    print("\n" + "-"*70)
    print(f"  [p] Change phrase (current: {current_phrase_idx+1}/{len(TEST_PHRASES)})")
    print(f"  [af] Play all American Female    [bf] Play all British Female")
    print(f"  [am] Play all American Male      [bm] Play all British Male")
    print(f"  [a] Play ALL voices              [q] Quit")
    print("-"*70)
    print(f"Phrase: \"{TEST_PHRASES[current_phrase_idx]}\"")

def play_category(prefix: str, name: str):
    """Play all voices starting with prefix."""
    print(f"\nPlaying all {name} voices...")
    for vid, grade, desc in VOICES:
        if vid.startswith(prefix):
            print(f"  {vid} ({grade})...", end=" ", flush=True)
            play_voice(vid, TEST_PHRASES[current_phrase_idx])
            print("done")

def main():
    global current_phrase_idx

    show_menu()

    while True:
        try:
            choice = input("\nChoice: ").strip().lower()

            if choice == 'q':
                print("Goodbye!")
                break
            elif choice == 'p':
                current_phrase_idx = (current_phrase_idx + 1) % len(TEST_PHRASES)
                print(f"\nNew phrase: \"{TEST_PHRASES[current_phrase_idx]}\"")
            elif choice == 'a':
                print("\nPlaying all voices...")
                for vid, grade, desc in VOICES:
                    print(f"  {vid} ({grade})...", end=" ", flush=True)
                    play_voice(vid, TEST_PHRASES[current_phrase_idx])
                    print("done")
            elif choice == 'af':
                play_category('af_', 'American Female')
            elif choice == 'bf':
                play_category('bf_', 'British Female')
            elif choice == 'am':
                play_category('am_', 'American Male')
            elif choice == 'bm':
                play_category('bm_', 'British Male')
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(VOICES):
                    vid, grade, desc = VOICES[idx]
                    print(f"  Playing {vid}...", end=" ", flush=True)
                    play_voice(vid, TEST_PHRASES[current_phrase_idx])
                    print("done")
                else:
                    print(f"Invalid number (1-{len(VOICES)})")
            elif choice == '':
                show_menu()
            else:
                print("Unknown command. Press Enter to see menu.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
