#!/usr/bin/env python3
"""
Test Kokoro voices - generates samples of top-tier voices for comparison.
Outputs WAV files to ./voice_samples/
"""

import os
from pathlib import Path

# Create output directory
output_dir = Path("voice_samples")
output_dir.mkdir(exist_ok=True)

# Test phrase that shows voice quality well
TEST_TEXT = "Hello Commander. I'm IRIS, your AI companion for Star Atlas. How can I assist you today?"

# Top voices to test (by grade)
VOICES_TO_TEST = [
    # A-grade (best)
    ("af_heart", "A"),
    ("af_bella", "A-"),
    # B-grade
    ("af_nicole", "B"),
    ("af_sky", "B"),
    ("bf_emma", "B-"),
    ("bf_isabella", "B-"),
    ("am_adam", "B-"),
    # C+ grade (best males)
    ("am_fenrir", "C+"),
    ("am_michael", "C+"),
    ("am_puck", "C+"),
]

print("Loading Kokoro model (on CPU for sampling)...")
from kokoro import KPipeline

# Initialize pipeline on CPU (GPU used by running Chatterbox)
pipe = KPipeline(lang_code='a', device='cpu')  # 'a' for American English

print(f"Generating {len(VOICES_TO_TEST)} voice samples...\n")

for voice_id, grade in VOICES_TO_TEST:
    print(f"  {voice_id} (Grade {grade})... ", end="", flush=True)
    try:
        # Generate audio
        generator = pipe(TEST_TEXT, voice=voice_id)

        # Collect all audio chunks
        import numpy as np
        audio_chunks = []
        for _, _, audio in generator:
            audio_chunks.append(audio)

        if audio_chunks:
            # Concatenate and save
            full_audio = np.concatenate(audio_chunks)

            # Save as WAV
            output_path = output_dir / f"{grade}_{voice_id}.wav"
            import scipy.io.wavfile as wavfile
            # Kokoro outputs at 24kHz
            wavfile.write(str(output_path), 24000, (full_audio * 32767).astype(np.int16))
            print(f"saved to {output_path}")
        else:
            print("no audio generated")
    except Exception as e:
        print(f"ERROR: {e}")

print(f"\nDone! Voice samples saved to: {output_dir.absolute()}")
print("Play them to compare: e.g., `aplay voice_samples/A_af_heart.wav`")
