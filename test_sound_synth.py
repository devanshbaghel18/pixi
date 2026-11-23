#!/usr/bin/env python3
"""
test_sound_synth.py — Unit Tests for Procedural 8-Bit Retro Sound Synthesizer
"""

import io
import os
import shutil
import struct
import sys
import tempfile
import unittest
import wave

# Ensure current worktree directory is top of sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sound_synth import (
    SAMPLE_RATE,
    SoundManager,
    SoundType,
    create_wav_bytes,
    generate_sine_sample,
    generate_square_sample,
    generate_triangle_sample,
    get_sound_manager,
    play_chime,
    synthesize_blush,
    synthesize_celebrate,
    synthesize_click,
    synthesize_greeting,
    synthesize_jump,
    synthesize_study_bell,
)
from dialogue_engine import DialogueEngine, Emotion


class TestSoundSynth(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_synth_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_wave_generators(self):
        """Tests that mathematical wave generators return bounded float values."""
        t_values = [0.0, 0.001, 0.005, 0.01, 0.05]
        freq = 440.0
        for t in t_values:
            sine = generate_sine_sample(freq, t)
            self.assertGreaterEqual(sine, -1.0)
            self.assertLessEqual(sine, 1.0)

            square = generate_square_sample(freq, t)
            self.assertIn(round(square, 2), (-0.7, 0.7))

            tri = generate_triangle_sample(freq, t)
            self.assertGreaterEqual(tri, -1.0)
            self.assertLessEqual(tri, 1.0)

    def test_create_wav_bytes(self):
        """Verifies that create_wav_bytes produces a valid 16-bit PCM WAV header and data."""
        samples = [0.0, 0.5, -0.5, 1.0, -1.0, 0.25]
        wav_bytes = create_wav_bytes(samples, sample_rate=22050)
        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav_bytes[:16])

        # Validate with wave module
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)  # 16-bit
            self.assertEqual(wf.getframerate(), 22050)
            self.assertEqual(wf.getnframes(), len(samples))

    def _validate_sound_format(self, wav_bytes: bytes, min_duration: float = 0.01):
        """Helper to validate wave audio bytes structure and playback duration."""
        self.assertIsInstance(wav_bytes, bytes)
        self.assertGreater(len(wav_bytes), 44)  # WAV header is 44 bytes minimum
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), SAMPLE_RATE)
            frames = wf.getnframes()
            duration = frames / wf.getframerate()
            self.assertGreaterEqual(duration, min_duration)

    def test_synthesizer_functions(self):
        """Verifies all procedural sound effect generators output valid PCM WAV bytes."""
        greeting_bytes = synthesize_greeting()
        self._validate_sound_format(greeting_bytes, min_duration=0.2)

        jump_bytes = synthesize_jump()
        self._validate_sound_format(jump_bytes, min_duration=0.15)

        blush_bytes = synthesize_blush()
        self._validate_sound_format(blush_bytes, min_duration=0.25)

        celebrate_bytes = synthesize_celebrate()
        self._validate_sound_format(celebrate_bytes, min_duration=0.4)

        study_bell_bytes = synthesize_study_bell()
        self._validate_sound_format(study_bell_bytes, min_duration=1.0)

        click_bytes = synthesize_click()
        self._validate_sound_format(click_bytes, min_duration=0.01)

    def test_sound_manager_cache_and_paths(self):
        """Verifies SoundManager caches .wav files to disk and resolves them."""
        mgr = SoundManager(cache_dir=self.temp_dir)
        self.assertTrue(os.path.isdir(self.temp_dir))

        # Check all enum types have generated cache files
        for st in SoundType:
            path = mgr.get_sound_path(st)
            self.assertIsNotNone(path)
            self.assertTrue(os.path.exists(path), f"File {path} does not exist for {st}")
            self.assertGreater(os.path.getsize(path), 44)

    def test_sound_manager_play(self):
        """Verifies play method executes non-blocking and blocking without uncaught errors."""
        mgr = SoundManager(cache_dir=self.temp_dir)
        # Mock player to None to test terminal bell / silent fallback
        mgr.audio_player = None
        res = mgr.play(SoundType.CLICK, non_blocking=False)
        self.assertFalse(res)  # False indicates fallback used

        # Test with dummy executable that returns 0 (like true)
        mgr.audio_player = shutil.which("true") or "/bin/true"
        res_true = mgr.play(SoundType.GREETING, non_blocking=False)
        self.assertTrue(res_true)

    def test_play_chime_convenience(self):
        """Verifies the global play_chime convenience wrapper executes cleanly."""
        res = play_chime(SoundType.CLICK, non_blocking=False)
        self.assertIsInstance(res, bool)

    def test_dialogue_engine_suggested_sound(self):
        """Verifies DialogueEngine determines the correct suggested_sound for various interactions."""
        engine = DialogueEngine(db_path=None, classifier=None)

        # Greeting should suggest GREETING
        res_greet = engine.process_message("Hello Mia! Good morning!")
        self.assertEqual(res_greet["suggested_sound"], "GREETING")

        # Love/Affection should suggest BLUSH
        res_love = engine.process_message("I love you so much Mia!")
        self.assertEqual(res_love["suggested_sound"], "BLUSH")

        # Excitement / exclamation should suggest JUMP
        res_jump = engine.process_message("This is totally amazing!")
        self.assertEqual(res_jump["suggested_sound"], "JUMP")

        # Neutral chat should suggest CLICK
        res_chat = engine.process_message("What are you thinking about right now?")
        self.assertEqual(res_chat["suggested_sound"], "CLICK")


if __name__ == "__main__":
    unittest.main()
