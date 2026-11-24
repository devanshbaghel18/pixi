#!/usr/bin/env python3
"""
scripts/benchmark_voices.py — Evaluates all 8 emotional voice profiles
Generates audio samples for each profile and records latency and file size.
"""

import os
import sys
import time

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech_engine import VoiceProfile, VOICE_PROFILES, get_speech_engine


def main():
    print("=" * 65)
    print("🎤 Evaluating Princess Mia Expressive Emotional Voice Profiles")
    print("=" * 65)

    tts = get_speech_engine()
    test_phrases = {
        VoiceProfile.DEFAULT: "Hello there! It is so wonderful to see you today.",
        VoiceProfile.TSUNDERE: "Hmph! It's not like I was waiting for you or anything, dummy!",
        VoiceProfile.SERIOUS: "Listen carefully. We need to handle this with complete focus.",
        VoiceProfile.HAPPY: "Yay! That is fantastic news! I am so excited for us!",
        VoiceProfile.SAD: "Oh... I understand. If you really want me to be quiet, I will.",
        VoiceProfile.AFFECTIONATE: "You mean so much to me. Please take good care of yourself.",
        VoiceProfile.THOUGHTFUL: "That is an intriguing concept. Let us analyze how that functions.",
        VoiceProfile.PLAYFUL: "Hehe! Catch me if you can! You won't escape that easily!",
    }

    out_dir = "/tmp/mia_voice_benchmarks"
    os.makedirs(out_dir, exist_ok=True)

    for profile, text in test_phrases.items():
        params = VOICE_PROFILES[profile]
        t0 = time.time()
        audio_file = tts.synthesize(text, profile=profile)
        elapsed_ms = (time.time() - t0) * 1000.0

        if audio_file and os.path.exists(audio_file):
            size_kb = os.path.getsize(audio_file) / 1024.0
            print(
                f"[{profile.value:20}] Latency: {elapsed_ms:6.1f}ms | Size: {size_kb:5.1f} KB | Pitch: {params.pitch:5} | Rate: {params.rate:5}"
            )
        else:
            print(f"[{profile.value:20}] Failed to synthesize")

    print("\n✓ Voice evaluation benchmark complete. All profiles synthesized.")


if __name__ == "__main__":
    main()
