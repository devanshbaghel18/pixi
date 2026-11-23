#!/usr/bin/env python3
"""
sound_synth.py — Procedural 8-Bit Retro Sound Synthesizer for Princess Mia

Generates expressive 8-bit audio chimes, celebratory fanfares, jump chirps,
and soothing study bells in pure Python using standard library (wave, math, struct).
Plays sounds asynchronously on Linux using PipeWire (pw-play), PulseAudio (paplay),
or ALSA (aplay) with graceful terminal bell fallback.

Zero external dependencies required.
"""

import io
import math
import os
import shutil
import struct
import subprocess
import tempfile
import threading
import wave
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

SAMPLE_RATE = 22050  # 22.05 kHz 16-bit mono PCM (retro 8-bit style)


class SoundType(str, Enum):
    GREETING = "GREETING"
    JUMP = "JUMP"
    BLUSH = "BLUSH"
    CELEBRATE = "CELEBRATE"
    STUDY_BELL = "STUDY_BELL"
    CLICK = "CLICK"


def generate_sine_sample(freq: float, t: float) -> float:
    return math.sin(2.0 * math.pi * freq * t)


def generate_square_sample(freq: float, t: float, duty: float = 0.5) -> float:
    period = 1.0 / max(1.0, freq)
    pos = (t % period) / period
    return 0.7 if pos < duty else -0.7


def generate_triangle_sample(freq: float, t: float) -> float:
    period = 1.0 / max(1.0, freq)
    pos = (t % period) / period
    return 4.0 * abs(pos - 0.5) - 1.0


def create_wav_bytes(samples: List[float], sample_rate: int = SAMPLE_RATE) -> bytes:
    """Encodes normalized float samples (-1.0 to +1.0) into 16-bit PCM WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)        # Mono
        wf.setsampwidth(2)        # 16-bit (2 bytes)
        wf.setframerate(sample_rate)

        raw_data = bytearray()
        for s in samples:
            # Clamp and convert to signed 16-bit integer (-32768 to 32767)
            clamped = max(-1.0, min(1.0, s))
            val = int(clamped * 32767.0)
            raw_data.extend(struct.pack("<h", val))

        wf.writeframes(raw_data)
    return buf.getvalue()


def synthesize_greeting(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Cheerful ascending 3-note arpeggio (C5=523Hz, E5=659Hz, G5=784Hz)."""
    notes = [
        (523.25, 0.08),  # C5
        (659.25, 0.08),  # E5
        (783.99, 0.16),  # G5
    ]
    samples = []
    for freq, duration in notes:
        total_samples = int(sample_rate * duration)
        for i in range(total_samples):
            t = i / sample_rate
            env = 1.0 - (i / total_samples) * 0.7  # gentle decay
            # Mix square wave with subtle sine
            val = (0.6 * generate_square_sample(freq, t, 0.4) + 0.4 * generate_sine_sample(freq, t)) * env
            samples.append(val)
    return create_wav_bytes(samples, sample_rate)


def synthesize_jump(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Energetic upward frequency slide (220Hz to 880Hz) with landing pop."""
    duration = 0.22
    total_samples = int(sample_rate * duration)
    samples = []

    f_start = 220.0
    f_end = 880.0

    for i in range(total_samples):
        progress = i / total_samples
        # Exponential pitch curve
        freq = f_start * ((f_end / f_start) ** progress)
        t = i / sample_rate
        env = 1.0 - progress * 0.5
        val = generate_square_sample(freq, t, 0.35) * env
        samples.append(val)
    return create_wav_bytes(samples, sample_rate)


def synthesize_blush(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Sweet gentle chime with warm vibrato (587Hz D5 with 6Hz vibrato)."""
    duration = 0.35
    total_samples = int(sample_rate * duration)
    samples = []

    base_freq = 587.33  # D5
    vib_rate = 6.0
    vib_depth = 14.0

    for i in range(total_samples):
        t = i / sample_rate
        freq = base_freq + math.sin(2.0 * math.pi * vib_rate * t) * vib_depth
        env = math.sin(math.pi * (i / total_samples))  # soft bell curve
        val = (0.7 * generate_sine_sample(freq, t) + 0.3 * generate_triangle_sample(freq * 2.0, t)) * env
        samples.append(val)
    return create_wav_bytes(samples, sample_rate)


def synthesize_celebrate(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Triumphant 4-note victory fanfare (G4 -> C5 -> E5 -> G5)."""
    notes = [
        (392.00, 0.09),  # G4
        (523.25, 0.09),  # C5
        (659.25, 0.09),  # E5
        (783.99, 0.28),  # G5 high cheer
    ]
    samples = []
    for idx, (freq, duration) in enumerate(notes):
        total_samples = int(sample_rate * duration)
        for i in range(total_samples):
            t = i / sample_rate
            env = 1.0 - (i / total_samples) * 0.4
            val = (0.65 * generate_square_sample(freq, t, 0.5) + 0.35 * generate_triangle_sample(freq, t)) * env
            samples.append(val)
    return create_wav_bytes(samples, sample_rate)


def synthesize_study_bell(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Calming, resonant mindfulness bell (440Hz A4 with rich harmonics & 1.8s decay)."""
    duration = 1.8
    total_samples = int(sample_rate * duration)
    samples = []

    f1 = 440.0   # Fundamental A4
    f2 = 880.0   # Octave
    f3 = 1320.0  # Fifth
    f4 = 1760.0  # High overtone

    for i in range(total_samples):
        t = i / sample_rate
        # Exponential decay envelope
        decay = math.exp(-3.5 * (i / total_samples))
        val = (
            0.50 * generate_sine_sample(f1, t) +
            0.25 * generate_sine_sample(f2, t) +
            0.15 * generate_sine_sample(f3, t) +
            0.10 * generate_sine_sample(f4, t)
        ) * decay
        samples.append(val)
    return create_wav_bytes(samples, sample_rate)


def synthesize_click(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Short 15ms retro UI selection tick."""
    duration = 0.015
    total_samples = int(sample_rate * duration)
    samples = []
    for i in range(total_samples):
        t = i / sample_rate
        freq = 1200.0 - (i / total_samples) * 600.0
        env = 1.0 - (i / total_samples)
        samples.append(generate_triangle_sample(freq, t) * env)
    return create_wav_bytes(samples, sample_rate)


SYNTHESIZERS = {
    SoundType.GREETING: synthesize_greeting,
    SoundType.JUMP: synthesize_jump,
    SoundType.BLUSH: synthesize_blush,
    SoundType.CELEBRATE: synthesize_celebrate,
    SoundType.STUDY_BELL: synthesize_study_bell,
    SoundType.CLICK: synthesize_click,
}


class SoundManager:
    """
    Manages cached audio assets and handles non-blocking Linux sound playback.
    Autodetects audio backends: PipeWire (pw-play), PulseAudio (paplay), or ALSA (aplay).
    """

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = os.path.join(tempfile.gettempdir(), "princess_mia_audio")
        os.makedirs(self.cache_dir, exist_ok=True)

        self.audio_player = self._detect_player()
        self._cached_files: Dict[str, str] = {}
        self._pregenerate_cache()

    def _detect_player(self) -> Optional[str]:
        for candidate in ("pw-play", "paplay", "aplay"):
            if shutil.which(candidate):
                return candidate
        return None

    def _pregenerate_cache(self) -> None:
        """Pregenerates and caches all procedural WAV files on disk."""
        for sound_type, synth_fn in SYNTHESIZERS.items():
            key = sound_type.value if hasattr(sound_type, "value") else str(sound_type)
            filepath = os.path.join(self.cache_dir, f"{key.lower()}.wav")
            try:
                wav_bytes = synth_fn()
                with open(filepath, "wb") as f:
                    f.write(wav_bytes)
                self._cached_files[key] = filepath
            except Exception:
                pass

    def get_sound_path(self, sound_type: Union[SoundType, str]) -> Optional[str]:
        key = sound_type.value if hasattr(sound_type, "value") else str(sound_type).upper()
        if key in self._cached_files and os.path.exists(self._cached_files[key]):
            return self._cached_files[key]

        synth_fn = SYNTHESIZERS.get(SoundType(key)) if key in SoundType.__members__ else None
        if synth_fn:
            filepath = os.path.join(self.cache_dir, f"{key.lower()}.wav")
            with open(filepath, "wb") as f:
                f.write(synth_fn())
            self._cached_files[key] = filepath
            return filepath
        return None

    def play(self, sound_type: Union[SoundType, str], non_blocking: bool = True) -> bool:
        """
        Plays the specified sound effect.
        If non_blocking=True (default), plays on a background daemon thread.
        """
        filepath = self.get_sound_path(sound_type)
        if not filepath or not self.audio_player:
            # Fallback to terminal bell
            try:
                print("\a", end="", flush=True)
            except Exception:
                pass
            return False

        def _play_proc():
            try:
                subprocess.run(
                    [self.audio_player, filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass

        if non_blocking:
            t = threading.Thread(target=_play_proc, daemon=True)
            t.start()
        else:
            _play_proc()
        return True


# Global singleton sound manager
_global_sound_manager: Optional[SoundManager] = None

def get_sound_manager() -> SoundManager:
    global _global_sound_manager
    if _global_sound_manager is None:
        _global_sound_manager = SoundManager()
    return _global_sound_manager

def play_chime(sound_type: Union[SoundType, str] = SoundType.GREETING, non_blocking: bool = True) -> bool:
    """Convenience function to play a procedural sound effect."""
    mgr = get_sound_manager()
    return mgr.play(sound_type, non_blocking=non_blocking)
