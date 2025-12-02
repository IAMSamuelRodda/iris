#!/usr/bin/env python3
"""Direct TTS test script - bypasses web layer entirely."""

import sys
import wave
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tts import TextToSpeech, get_tts

def main():
    print("=" * 60)
    print("DIRECT TTS TEST")
    print("=" * 60)

    # Initialize TTS (will load model)
    print("\n[1] Initializing TTS...")
    tts = TextToSpeech(device="cpu")

    # Test synthesis
    test_text = "Hello Commander Sam. This is a test of the text to speech system."
    print(f"\n[2] Synthesizing: '{test_text}'")

    result = tts.synthesize(test_text)

    print(f"\n[3] Synthesis Result:")
    print(f"    - Sample rate: {result.sample_rate} Hz")
    print(f"    - Duration: {result.duration_seconds:.2f} seconds")
    print(f"    - Audio shape: {result.audio.shape}")
    print(f"    - Audio dtype: {result.audio.dtype}")
    print(f"    - Audio min/max: {result.audio.min():.4f} / {result.audio.max():.4f}")

    # Convert to WAV bytes
    print("\n[4] Converting to WAV bytes...")
    wav_bytes = result.to_wav_bytes()
    print(f"    - WAV size: {len(wav_bytes)} bytes")

    # Save to file
    output_path = Path("/tmp/tts_direct_test.wav")
    output_path.write_bytes(wav_bytes)
    print(f"    - Saved to: {output_path}")

    # Verify WAV file structure
    print("\n[5] Verifying WAV file structure...")
    with wave.open(str(output_path), 'rb') as wf:
        print(f"    - Channels: {wf.getnchannels()}")
        print(f"    - Sample width: {wf.getsampwidth()} bytes ({wf.getsampwidth() * 8} bits)")
        print(f"    - Frame rate: {wf.getframerate()} Hz")
        print(f"    - Frames: {wf.getnframes()}")
        print(f"    - Duration: {wf.getnframes() / wf.getframerate():.2f} seconds")

        # Read and verify audio data
        raw_data = wf.readframes(wf.getnframes())
        audio_array = np.frombuffer(raw_data, dtype=np.int16)
        print(f"    - Audio samples: {len(audio_array)}")
        print(f"    - Audio min/max: {audio_array.min()} / {audio_array.max()}")

        # Check for silence or clipping
        if audio_array.max() == audio_array.min():
            print("    - WARNING: Audio is silent (all samples identical)")
        elif abs(audio_array.max()) > 32000 or abs(audio_array.min()) > 32000:
            print("    - WARNING: Audio may be clipping")
        else:
            print("    - Audio levels look normal")

    # Also save raw PCM (what we send over WebSocket)
    print("\n[6] Extracting raw PCM (what WebSocket sends)...")
    pcm_data = wav_bytes[44:]  # Strip 44-byte WAV header
    pcm_path = Path("/tmp/tts_direct_test.pcm")
    pcm_path.write_bytes(pcm_data)
    print(f"    - PCM size: {len(pcm_data)} bytes")
    print(f"    - Saved to: {pcm_path}")

    # Verify PCM data
    pcm_array = np.frombuffer(pcm_data, dtype=np.int16)
    print(f"    - PCM samples: {len(pcm_array)}")
    print(f"    - PCM min/max: {pcm_array.min()} / {pcm_array.max()}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nTo play the audio:")
    print(f"  aplay {output_path}")
    print(f"  # or: ffplay -nodisp {output_path}")
    print(f"\nTo convert PCM to WAV for playback:")
    print(f"  ffmpeg -f s16le -ar 24000 -ac 1 -i {pcm_path} /tmp/pcm_converted.wav")

if __name__ == "__main__":
    main()
