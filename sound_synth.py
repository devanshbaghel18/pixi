#!/usr/bin/env python3
"""
sound_synth.py — Procedural 8-Bit Retro Sound Synthesizer for Princess Mia

Generates expressive 8-bit audio chimes, celebratory fanfares, jump chirps,
blushing vibrato warbles, and soothing study bells in pure Python using the
standard library (wave, math, struct). Plays sounds asynchronously on Linux
using PipeWire (pw-play), PulseAudio (paplay), or ALSA (aplay) with graceful
terminal bell fallback and zero external dependencies required.
"""

import io
import math
import os
import random
import shutil
import struct
import subprocess
import tempfile
import threading
import wave
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Union

SAMPLE_RATE = 22050  # 22.05 kHz 16-bit mono PCM (classic 8-bit retro style)


class SoundType(str, Enum):
    GREETING = "GREETING"
    JUMP = "JUMP"
    BLUSH = "BLUSH"
    CELEBRATE = "CELEBRATE"
    STUDY_BELL = "STUDY_BELL"
    CLICK = "CLICK"


# ---------------------------------------------------------------------------
# Procedural Audio Oscillators
# ---------------------------------------------------------------------------

def generate_sine_sample(freq: float, t: float) -> float:
    """Generates a pure sinusoidal wave sample."""
    return math.sin(2.0 * math.pi * freq * t)


def generate_square_sample(freq: float, t: float, duty: float = 0.5) -> float:
    """Generates a classic chiptune pulse/square wave sample with variable duty cycle."""
    period = 1.0 / max(1.0, freq)
    pos = (t % period) / period
    return 0.7 if pos < duty else -0.7


def generate_triangle_sample(freq: float, t: float) -> float:
    """Generates a triangle wave sample for warm retro melodic bass."""
    period = 1.0 / max(1.0, freq)
    pos = (t % period) / period
    return 4.0 * abs(pos - 0.5) - 1.0


def generate_sawtooth_sample(freq: float, t: float) -> float:
    """Generates a sawtooth wave sample for bright chiptune brass/leads."""
    period = 1.0 / max(1.0, freq)
    pos = (t % period) / period
    return 2.0 * pos - 1.0


def generate_noise_sample() -> float:
    """Generates a white noise sample for percussive retro sound effects."""
    return random.uniform(-0.8, 0.8)


def create_wav_bytes(
    samples: List[float],
    sample_rate: int = SAMPLE_RATE,
    volume: float = 1.0,
) -> bytes:
    """
    Encodes normalized float samples (-1.0 to +1.0) into 16-bit PCM WAV bytes.
    Applies volume scaling and hard-clipping protection.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)        # Mono
        wf.setsampwidth(2)        # 16-bit (2 bytes per sample)
        wf.setframerate(sample_rate)

        raw_data = bytearray()
        vol = max(0.0, min(1.0, float(volume)))
        for s in samples:
            clamped = max(-1.0, min(1.0, s * vol))
            val = int(clamped * 32767.0)
            raw_data.extend(struct.pack("<h", val))

        wf.writeframes(raw_data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Procedural Retro Sound Effect Generators
# ---------------------------------------------------------------------------

def synthesize_greeting(sample_rate: int = SAMPLE_RATE) -> bytes:
    """
    Cheerful ascending 3-note arpeggio (C5=523Hz, E5=659Hz, G5=784Hz).
    Iconic welcoming retro chime when Mia says hello or greets the user.
    """
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
            env = 1.0 - (i / total_samples) * 0.7  # gentle linear decay
            val = (0.6 * generate_square_sample(freq, t, 0.4) + 0.4 * generate_sine_sample(freq, t)) * env
            samples.append(val)
    return create_wav_bytes(samples, sample_rate)


def synthesize_jump(sample_rate: int = SAMPLE_RATE) -> bytes:
    """
    Energetic upward frequency slide (220Hz to 880Hz) with landing pop.
    Classic platformer physics jump sound for excitement and energetic actions.
    """
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
    """
    Sweet gentle chime with warm vibrato (587Hz D5 with 6Hz LFO vibrato).
    Cute, shy, flustered warble when Mia receives romantic compliments.
    """
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
    """
    Triumphant 4-note victory fanfare (G4 -> C5 -> E5 -> G5).
    Celebratory retro fanfare for twirls, level-ups, and achievements.
    """
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
    """
    Calming, resonant mindfulness bell (440Hz A4 with rich harmonics & 1.8s decay).
    Harmonic Japanese school / meditation chime for study sessions and timers.
    """
    duration = 1.8
    total_samples = int(sample_rate * duration)
    samples = []

    f1 = 440.0   # Fundamental A4
    f2 = 880.0   # Octave
    f3 = 1320.0  # Fifth
    f4 = 1760.0  # High overtone

    for i in range(total_samples):
        t = i / sample_rate
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


# Direct generator aliases matching task nomenclature
generate_greeting_arpeggio = synthesize_greeting
generate_jump_chirp = synthesize_jump
generate_blushing_vibrato = synthesize_blush
generate_celebration_fanfare = synthesize_celebrate
generate_study_bell = synthesize_study_bell
generate_click = synthesize_click

SYNTHESIZERS: Dict[SoundType, Callable[[int], bytes]] = {
    SoundType.GREETING: synthesize_greeting,
    SoundType.JUMP: synthesize_jump,
    SoundType.BLUSH: synthesize_blush,
    SoundType.CELEBRATE: synthesize_celebrate,
    SoundType.STUDY_BELL: synthesize_study_bell,
    SoundType.CLICK: synthesize_click,
}

# Aliases mapping loose strings to SoundType
SOUND_ALIAS_MAP: Dict[str, SoundType] = {
    "GREETING": SoundType.GREETING,
    "GREET": SoundType.GREETING,
    "HELLO": SoundType.GREETING,
    "HI": SoundType.GREETING,
    "ARPEGGIO": SoundType.GREETING,
    "JUMP": SoundType.JUMP,
    "JUMPING": SoundType.JUMP,
    "JUMP_CHIRP": SoundType.JUMP,
    "CHIRP": SoundType.JUMP,
    "EXCITEMENT": SoundType.JUMP,
    "BLUSH": SoundType.BLUSH,
    "BLUSHING": SoundType.BLUSH,
    "VIBRATO": SoundType.BLUSH,
    "LOVE": SoundType.BLUSH,
    "SHY": SoundType.BLUSH,
    "CELEBRATE": SoundType.CELEBRATE,
    "CELEBRATION": SoundType.CELEBRATE,
    "CELEBRATING": SoundType.CELEBRATE,
    "FANFARE": SoundType.CELEBRATE,
    "VICTORY": SoundType.CELEBRATE,
    "PARTY": SoundType.CELEBRATE,
    "STUDY_BELL": SoundType.STUDY_BELL,
    "STUDY": SoundType.STUDY_BELL,
    "BELL": SoundType.STUDY_BELL,
    "CHIME": SoundType.STUDY_BELL,
    "MINDFULNESS": SoundType.STUDY_BELL,
    "CLICK": SoundType.CLICK,
    "TAP": SoundType.CLICK,
}


def normalize_sound_type(sound_type: Union[SoundType, str]) -> SoundType:
    """Normalizes any string or SoundType into a recognized SoundType enum member."""
    if isinstance(sound_type, SoundType):
        return sound_type
    s = str(sound_type).strip().upper()
    return SOUND_ALIAS_MAP.get(s, SoundType.GREETING)


# ---------------------------------------------------------------------------
# Sound Manager & Audio Playback Engine
# ---------------------------------------------------------------------------

class SoundManager:
    """
    Manages procedural 8-bit audio generation, disk caching, and non-blocking
    Linux playback. Autodetects PipeWire (pw-play), PulseAudio (paplay), or ALSA (aplay).
    """

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = os.path.join(tempfile.gettempdir(), "princess_mia_audio")
        os.makedirs(self.cache_dir, exist_ok=True)

        self.audio_player: Optional[str] = self._detect_player()
        self.sound_enabled: bool = True
        self.volume: float = 1.0
        self._cached_files: Dict[str, str] = {}
        self._cached_bytes: Dict[str, bytes] = {}
        self._pregenerate_cache()

    def _detect_player(self) -> Optional[str]:
        """Detects available Linux audio playback commands."""
        for candidate in ("pw-play", "paplay", "aplay"):
            if shutil.which(candidate):
                return candidate
        return None

    def _pregenerate_cache(self) -> None:
        """Pregenerates and caches all procedural WAV files on disk and in memory."""
        for sound_type, synth_fn in SYNTHESIZERS.items():
            key = sound_type.value
            filepath = os.path.join(self.cache_dir, f"{key.lower()}.wav")
            try:
                wav_bytes = synth_fn(SAMPLE_RATE)
                self._cached_bytes[key] = wav_bytes
                with open(filepath, "wb") as f:
                    f.write(wav_bytes)
                self._cached_files[key] = filepath
            except Exception:
                pass

    def get_sound_path(self, sound_type: Union[SoundType, str]) -> Optional[str]:
        """Returns the file path for the given sound, synthesizing and caching if missing."""
        st = normalize_sound_type(sound_type)
        key = st.value
        if key in self._cached_files and os.path.exists(self._cached_files[key]):
            return self._cached_files[key]

        synth_fn = SYNTHESIZERS.get(st)
        if synth_fn:
            filepath = os.path.join(self.cache_dir, f"{key.lower()}.wav")
            try:
                data = synth_fn(SAMPLE_RATE)
                self._cached_bytes[key] = data
                with open(filepath, "wb") as f:
                    f.write(data)
                self._cached_files[key] = filepath
                return filepath
            except Exception:
                return None
        return None

    def get_wav_bytes(self, sound_type: Union[SoundType, str]) -> Optional[bytes]:
        """Retrieves raw WAV bytes for the specified sound effect."""
        st = normalize_sound_type(sound_type)
        key = st.value
        if key in self._cached_bytes:
            return self._cached_bytes[key]
        path = self.get_sound_path(st)
        if path and os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    data = f.read()
                    self._cached_bytes[key] = data
                    return data
            except Exception:
                pass
        synth_fn = SYNTHESIZERS.get(st)
        if synth_fn:
            data = synth_fn(SAMPLE_RATE)
            self._cached_bytes[key] = data
            return data
        return None

    def save_sound_to_file(self, sound_type: Union[SoundType, str], filepath: str) -> str:
        """Saves a procedural sound effect WAV directly to a target destination."""
        data = self.get_wav_bytes(sound_type)
        if not data:
            raise ValueError(f"Unknown sound type: {sound_type}")
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(data)
        return filepath

    def list_sounds(self) -> List[str]:
        """Lists all supported sound effect names."""
        return [st.value for st in SoundType]

    def has_sound(self, sound_name: str) -> bool:
        """Checks if a sound effect or alias is supported."""
        if not sound_name:
            return False
        s = str(sound_name).strip().upper()
        return s in SOUND_ALIAS_MAP or s in SoundType.__members__

    def set_sound_enabled(self, enabled: bool) -> None:
        """Enables or disables sound playback."""
        self.sound_enabled = bool(enabled)

    def is_sound_enabled(self) -> bool:
        """Returns True if sound playback is enabled."""
        return self.sound_enabled

    def toggle_sound(self) -> bool:
        """Toggles sound enabled state and returns new state."""
        self.sound_enabled = not self.sound_enabled
        return self.sound_enabled

    def set_volume(self, volume: float) -> None:
        """Sets playback volume factor between 0.0 and 1.0."""
        self.volume = max(0.0, min(1.0, float(volume)))

    def get_volume(self) -> float:
        """Returns the current playback volume factor."""
        return self.volume

    def play(
        self,
        sound_type: Union[SoundType, str] = SoundType.GREETING,
        non_blocking: bool = True,
    ) -> bool:
        """
        Plays the specified sound effect.
        If non_blocking=True (default), runs asynchronously on a daemon thread.
        Returns True if playback was initiated, False if sound disabled or player failed.
        """
        if not self.sound_enabled:
            return False

        filepath = self.get_sound_path(sound_type)
        if not filepath or not self.audio_player:
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
                try:
                    print("\a", end="", flush=True)
                except Exception:
                    pass

        if non_blocking:
            t = threading.Thread(target=_play_proc, daemon=True)
            t.start()
        else:
            _play_proc()
        return True

    def play_sound(
        self,
        sound_type: Union[SoundType, str] = SoundType.GREETING,
        non_blocking: bool = True,
    ) -> bool:
        """Convenience alias for play()."""
        return self.play(sound_type, non_blocking=non_blocking)


# ---------------------------------------------------------------------------
# Global Singleton & Module Helper Functions
# ---------------------------------------------------------------------------

_global_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Returns the shared singleton SoundManager instance."""
    global _global_sound_manager
    if _global_sound_manager is None:
        _global_sound_manager = SoundManager()
    return _global_sound_manager


def play_chime(
    sound_type: Union[SoundType, str] = SoundType.GREETING,
    non_blocking: bool = True,
) -> bool:
    """Convenience function to play a procedural sound effect."""
    mgr = get_sound_manager()
    return mgr.play(sound_type, non_blocking=non_blocking)


def play_sound(
    sound_type: Union[SoundType, str] = SoundType.GREETING,
    non_blocking: bool = True,
) -> bool:
    """Convenience function to play a procedural sound effect."""
    return play_chime(sound_type, non_blocking=non_blocking)


def set_sound_enabled(enabled: bool) -> None:
    """Globally enables or disables audio playback."""
    get_sound_manager().set_sound_enabled(enabled)


def is_sound_enabled() -> bool:
    """Returns whether audio playback is globally enabled."""
    return get_sound_manager().is_sound_enabled()


def toggle_sound() -> bool:
    """Toggles audio playback state globally."""
    return get_sound_manager().toggle_sound()


def set_volume(volume: float) -> None:
    """Sets global audio volume factor."""
    get_sound_manager().set_volume(volume)


def get_volume() -> float:
    """Returns global audio volume factor."""
    return get_sound_manager().get_volume()


def list_sounds() -> List[str]:
    """Returns list of all available sound types."""
    return get_sound_manager().list_sounds()
