#!/usr/bin/env python3
"""
speech_engine.py — Natural, Emotionally Expressive Speech Engine for Princess Mia
================================================================================
Features:
  - 100% Local / Free offline-capable operation: Zero paid cloud APIs or API keys.
  - Recognizable, consistent female voice identity:
      Youthful adult female voice, bright mid-to-high register, clear English pronunciation,
      subtle breathiness, expressive intonation, and anime-inspired charm without robotic delivery
      or childish squeakiness.
  - Expressive Voice Profiles:
      * DEFAULT_FEMALE      — Warm, conversational, clear, balanced pace.
      * TSUNDERE            — Expressive, defensive, slightly flustered, sharper consonants, quick pacing.
      * NATURAL_FIRM_FEMALE — Serious, grounded, firm articulation, slightly lower register, deliberate.
      * BRIGHT_FEMALE       — Lively, radiant energy, pitch variation, enthusiastic delivery.
      * SOFT_FEMALE         — Soft volume, slower pace, subtle emotional vulnerability.
      * WARM_FEMALE         — Tender, gentle, caring, natural affection.
      * CALM_FEMALE         — Measured, reflective, deep thoughtful delivery.
      * PLAYFUL_FEMALE      — Cheerful, teasing, spirited anime bounce.
  - Emotion-to-Voice Routing:
      Distinguishes user emotion from Mia's intended delivery (e.g. scolding does not make Mia shout).
  - Dual-tier synthesis:
      1. Primary Neural Engine: edge-tts (studio-grade neural synthesis with custom pitch/rate/volume prosody).
      2. 100% Offline Fallback: espeak-ng with profile-specific pitch, tempo, and formant modulation.
  - Non-blocking Asynchronous Generation & Playback:
      Runs on daemon threads; never freezes Tkinter UI animations, thinking bubble, or retro chimes.
  - Reusable Audio Caching & Cancellation:
      Caches audio in /tmp/mia_voice_cache/ and cleanly halts playback on new speech or exit.
"""

import asyncio
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

# Base Voice Identity
BASE_VOICE_ID = "en-US-AnaNeural"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "mia_voice_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


class VoiceProfile(str, Enum):
    """Supported expressive delivery styles for Princess Mia."""
    DEFAULT = "DEFAULT_FEMALE"
    TSUNDERE = "TSUNDERE"
    SERIOUS = "NATURAL_FIRM_FEMALE"
    HAPPY = "BRIGHT_FEMALE"
    SAD = "SOFT_FEMALE"
    AFFECTIONATE = "WARM_FEMALE"
    THOUGHTFUL = "CALM_FEMALE"
    PLAYFUL = "PLAYFUL_FEMALE"


@dataclass
class ProfileParameters:
    """Acoustic, prosodic and emotional delivery parameters."""
    rate: str           # e.g. "+8%", "-10%"
    pitch: str          # e.g. "+6Hz", "-4Hz"
    volume: str         # e.g. "+5%", "-15%"
    espeak_pitch: int   # 0 - 99
    espeak_speed: int   # Words per minute
    description: str    # Emotional voice acting direction


# Concrete acoustic prosody definitions for Mia's emotional delivery
VOICE_PROFILES: Dict[VoiceProfile, ProfileParameters] = {
    VoiceProfile.DEFAULT: ProfileParameters(
        rate="+2%",
        pitch="+2Hz",
        volume="+0%",
        espeak_pitch=78,
        espeak_speed=155,
        description="Warm, conversational young adult female voice with clear articulation and anime charm."
    ),
    VoiceProfile.TSUNDERE: ProfileParameters(
        rate="+12%",
        pitch="+6Hz",
        volume="+5%",
        espeak_pitch=84,
        espeak_speed=172,
        description="Expressive tsundere young adult woman. Defensive, slightly irritated and flustered with sharper consonants."
    ),
    VoiceProfile.SERIOUS: ProfileParameters(
        rate="-4%",
        pitch="-4Hz",
        volume="+10%",
        espeak_pitch=72,
        espeak_speed=142,
        description="Grounded, serious feminine voice with firm articulation and deliberate pacing."
    ),
    VoiceProfile.HAPPY: ProfileParameters(
        rate="+8%",
        pitch="+8Hz",
        volume="+6%",
        espeak_pitch=86,
        espeak_speed=165,
        description="Bright, radiant delivery with high natural energy and enthusiastic pitch variation."
    ),
    VoiceProfile.SAD: ProfileParameters(
        rate="-12%",
        pitch="-3Hz",
        volume="-18%",
        espeak_pitch=70,
        espeak_speed=134,
        description="Gentle, vulnerable delivery with softer volume, subtle emotional gravity and measured pace."
    ),
    VoiceProfile.AFFECTIONATE: ProfileParameters(
        rate="-6%",
        pitch="+1Hz",
        volume="-8%",
        espeak_pitch=76,
        espeak_speed=146,
        description="Warm, caring delivery with natural softness and tender intimacy."
    ),
    VoiceProfile.THOUGHTFUL: ProfileParameters(
        rate="-8%",
        pitch="-2Hz",
        volume="-2%",
        espeak_pitch=74,
        espeak_speed=144,
        description="Calm, measured, reflective pace suitable for explaining complex concepts."
    ),
    VoiceProfile.PLAYFUL: ProfileParameters(
        rate="+6%",
        pitch="+6Hz",
        volume="+3%",
        espeak_pitch=82,
        espeak_speed=162,
        description="Spirited, mischievous, teasing anime tone with cheerful energy."
    ),
}


def clean_text_for_speech(text: str) -> str:
    """
    Sanitizes assistant dialogue for natural voice synthesis:
      - Strips emojis and Unicode pictographs (e.g. 🌸, 💖, ✨).
      - Strips roleplay asterisks (e.g. *jumps for joy*, *sighs softly*).
      - Strips markdown formatting (bold, italic, code blocks, backticks).
      - Normalizes whitespace and trims excessive length.
    """
    if not text:
        return ""

    # Remove roleplay asterisks
    cleaned = re.sub(r"\*[^*]+\*", "", text)

    # Remove markdown code blocks and symbols
    cleaned = re.sub(r"```[\s\S]*?```", "", cleaned)
    cleaned = re.sub(r"[`#_~>]", "", cleaned)

    # Remove emojis and high Unicode code points
    cleaned = re.sub(
        r"[\U00010000-\U0010ffff]|[\u2600-\u27ff]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\ufe00-\ufe0f]|[\u200d]|[\u2022\u2023\u25aa\u25ab\u25cf\u25cb]",
        "",
        cleaned,
    )

    # Remove decorative companion symbols
    cleaned = re.sub(r"[✦✧♥❤★☆✿❀~·•\^]+", "", cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Truncate overly long responses to ~280 characters at sentence boundary for snappy conversational pacing
    if len(cleaned) > 280:
        sentences = re.split(r"([.!?])", cleaned)
        shortened = ""
        for i in range(0, len(sentences) - 1, 2):
            piece = sentences[i] + sentences[i + 1]
            if len(shortened) + len(piece) <= 280:
                shortened += piece + " "
            else:
                break
        cleaned = shortened.strip() or cleaned[:250] + "."

    return cleaned


def resolve_voice_profile(
    mia_emotion: str = "NORMAL",
    user_emotion: Optional[str] = None,
    text: Optional[str] = None,
) -> VoiceProfile:
    """
    Intelligently maps dialogue context and character mood to Mia's emotional voice profile.
    Separates user emotion from Mia's own delivery style:
      - User scolding / harsh input -> Mia responds with SAD (vulnerable/hurt), never mimicking anger.
      - User compliment / love -> Mia responds with AFFECTIONATE or PLAYFUL.
      - Playful / teasing remarks -> PLAYFUL.
      - Complex technical explanation -> THOUGHTFUL.
      - Tsundere triggers -> TSUNDERE.
    """
    norm_mia = (mia_emotion or "NORMAL").upper()
    norm_user = (user_emotion or "").upper()
    text_lower = (text or "").lower()

    # 1. Scolding / Hurt Boundary: If user scolded, Mia responds with vulnerable SAD delivery
    if norm_mia in ("SAD", "HURT") or norm_user == "SAD":
        return VoiceProfile.SAD

    # 2. Tsundere checks: defensive words like "dummy", "idiot", "b-baka", "not like i wanted"
    if any(k in text_lower for k in ("dummy", "idiot", "baka", "not like", "hmph", "shut up dummy")):
        return VoiceProfile.TSUNDERE

    # 3. Serious / Anger boundary
    if norm_mia in ("ANGRY", "SERIOUS"):
        return VoiceProfile.SERIOUS

    # 4. Affectionate delivery
    if norm_mia in ("LOVE", "SHY", "AFFECTIONATE"):
        return VoiceProfile.AFFECTIONATE

    # 5. Playful delivery
    if norm_mia in ("PLAYFUL", "TEASING"):
        return VoiceProfile.PLAYFUL

    # 6. Happy / Joyous delivery
    if norm_mia in ("HAPPY", "EXCITED"):
        return VoiceProfile.HAPPY

    # 7. Thoughtful / Academic delivery (heuristics for programming, science, explanation)
    if norm_mia == "THOUGHTFUL" or any(k in text_lower for k in ("quantum", "algorithm", "concept", "architecture", "actually", "reflect")):
        return VoiceProfile.THOUGHTFUL

    return VoiceProfile.DEFAULT


class SpeechEngine:
    """
    Main Speech Synthesis Engine for Princess Mia.
    Provides multi-profile neural speech synthesis with offline fallback.
    """

    def __init__(
        self,
        voice_id: str = BASE_VOICE_ID,
        enabled: bool = True,
    ):
        self.voice_id = voice_id
        self.enabled = enabled
        self._lock = threading.Lock()
        self.current_process: Optional[subprocess.Popen] = None
        self.player = self._detect_player()
        self.has_edge_tts = self._check_edge_tts()
        self.has_espeak = bool(shutil.which("espeak-ng") or shutil.which("espeak"))

    def _detect_player(self) -> Optional[str]:
        """Finds system CLI audio players on Linux."""
        for cmd in ("ffplay", "paplay", "aplay", "mpv"):
            if shutil.which(cmd):
                return cmd
        return None

    def _check_edge_tts(self) -> bool:
        """Verifies if edge_tts library is importable."""
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return bool(shutil.which("edge-tts"))

    def stop(self):
        """Halts any ongoing speech immediately."""
        with self._lock:
            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=0.3)
                except Exception:
                    try:
                        self.current_process.kill()
                    except Exception:
                        pass
                finally:
                    self.current_process = None

    def synthesize(
        self,
        text: str,
        profile: VoiceProfile = VoiceProfile.DEFAULT,
    ) -> Optional[str]:
        """
        Synthesizes text into an audio file using the selected emotional voice profile.
        Returns the path to the cached audio file, or None if synthesis failed.
        """
        if not text:
            return None

        clean = clean_text_for_speech(text)
        if not clean:
            return None

        params = VOICE_PROFILES.get(profile, VOICE_PROFILES[VoiceProfile.DEFAULT])

        # Generate cache key based on text, voice, and profile settings
        cache_key = hashlib.sha256(
            f"{self.voice_id}:{profile.value}:{params.rate}:{params.pitch}:{clean}".encode("utf-8")
        ).hexdigest()[:24]
        out_file = os.path.join(CACHE_DIR, f"mia_{cache_key}.mp3")

        # Reuse cached audio if already synthesized
        if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
            return out_file

        # Try edge-tts neural voice first
        if self.has_edge_tts:
            try:
                import edge_tts

                async def _gen():
                    comm = edge_tts.Communicate(
                        clean,
                        self.voice_id,
                        rate=params.rate,
                        pitch=params.pitch,
                        volume=params.volume,
                    )
                    await comm.save(out_file)

                asyncio.run(_gen())
                if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                    return out_file
            except Exception:
                pass

        # Offline fallback: espeak-ng WAV output
        if self.has_espeak:
            try:
                wav_file = os.path.join(CACHE_DIR, f"mia_{cache_key}.wav")
                bin_path = shutil.which("espeak-ng") or shutil.which("espeak")
                cmd = [
                    bin_path,
                    "-v", "en+f3",
                    "-p", str(params.espeak_pitch),
                    "-s", str(params.espeak_speed),
                    "-w", wav_file,
                    clean,
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(wav_file) and os.path.getsize(wav_file) > 0:
                    return wav_file
            except Exception:
                pass

        return None

    def play_audio(self, audio_path: str) -> bool:
        """Plays audio file synchronously via system player."""
        if not audio_path or not os.path.exists(audio_path):
            return False

        self.stop()

        play_cmd = []
        if self.player == "ffplay":
            play_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path]
        elif self.player == "paplay":
            play_cmd = ["paplay", audio_path]
        elif self.player == "mpv":
            play_cmd = ["mpv", "--no-video", "--really-quiet", audio_path]
        else:
            play_cmd = ["aplay", "-q", audio_path]

        try:
            with self._lock:
                self.current_process = subprocess.Popen(
                    play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            self.current_process.wait()
            with self._lock:
                self.current_process = None
            return True
        except Exception:
            with self._lock:
                self.current_process = None
            return False

    def speak(
        self,
        text: str,
        profile: VoiceProfile = VoiceProfile.DEFAULT,
    ) -> bool:
        """Synthesizes and speaks text synchronously."""
        if not self.enabled:
            return False
        audio_file = self.synthesize(text, profile=profile)
        if audio_file:
            return self.play_audio(audio_file)
        return False

    def speak_async(
        self,
        text: str,
        profile: VoiceProfile = VoiceProfile.DEFAULT,
        on_start: Optional[Callable[[], None]] = None,
        on_done: Optional[Callable[[bool], None]] = None,
    ) -> threading.Thread:
        """
        Asynchronously generates and speaks text in a background thread.
        Never blocks the Tkinter GUI thread or character animations.
        """
        def _worker():
            if on_start:
                try:
                    on_start()
                except Exception:
                    pass

            ok = False
            try:
                if self.enabled:
                    ok = self.speak(text, profile=profile)
            except Exception:
                ok = False
            finally:
                if on_done:
                    try:
                        on_done(ok)
                    except Exception:
                        pass

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return thread


# Singleton global speech engine
_global_speech_engine: Optional[SpeechEngine] = None


def get_speech_engine(voice_id: str = BASE_VOICE_ID, enabled: bool = True) -> SpeechEngine:
    """Returns the singleton SpeechEngine instance."""
    global _global_speech_engine
    if _global_speech_engine is None:
        _global_speech_engine = SpeechEngine(voice_id=voice_id, enabled=enabled)
    return _global_speech_engine
