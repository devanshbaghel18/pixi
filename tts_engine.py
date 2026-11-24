#!/usr/bin/env python3
"""
tts_engine.py — 100% Free Speech Synthesis Engine for Princess Mia
Features:
  - Zero paid dependencies or cloud API keys.
  - Primary Neural Engine: edge-tts (free natural female voices, e.g. en-US-AnaNeural).
  - Offline Local Fallback: espeak-ng / pyttsx3 (100% offline Linux speech synthesis).
  - Clean text filtering: strips emojis, markdown symbols, and action asterisks.
  - Asynchronous background worker: never blocks GUI animation loops or audio chimes.
  - Stop/Mute capabilities: cleanly cancels active speech playback.
"""

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
import threading
from typing import Callable, Optional

# Constants
DEFAULT_VOICE = "en-US-AnaNeural"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "mia_tts_cache")


def clean_text_for_speech(text: str) -> str:
    """
    Cleans dialogue text for natural speech synthesis:
      - Strips emojis and decorative Unicode symbols
      - Removes markdown bold/italics (e.g. *jumps for joy*)
      - Removes extra whitespaces and URL/code fragments
    """
    if not text:
        return ""

    # Remove action asterisks like *jumps* or *blushes*
    cleaned = re.sub(r"\*[^*]+\*", "", text)

    # Remove markdown bold/italic tags
    cleaned = re.sub(r"[\*_`#]", "", cleaned)

    # Remove emojis and high Unicode symbols
    cleaned = re.sub(
        r"[\U00010000-\U0010ffff]|[\u2600-\u27ff]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\ufe00-\ufe0f]|[\u200d]|[\u2022\u2023\u25aa\u25ab\u25cf\u25cb]",
        "",
        cleaned,
    )

    # Remove common decorative symbols like ✦, ✧, ♥, ★, ✿, 🌸
    cleaned = re.sub(r"[✦✧♥❤★☆✿❀~·•\^]+", "", cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Limit maximum spoken length to ~250 characters for responsive chat flow
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


class TTSEngine:
    """
    Unified speech synthesis engine supporting high-definition neural TTS
    and offline Linux fallback without any paid services or API keys.
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        enabled: bool = True,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self.voice = voice
        self.enabled = enabled
        self.rate = rate
        self.pitch = pitch
        self.current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

        os.makedirs(CACHE_DIR, exist_ok=True)

        # Check local system players
        self.player = self._detect_audio_player()
        self.has_edge_tts = self._check_edge_tts()
        self.has_espeak = bool(shutil.which("espeak-ng") or shutil.which("espeak"))

    def _detect_audio_player(self) -> Optional[str]:
        """Detects installed Linux command-line audio players."""
        for cmd in ("ffplay", "paplay", "aplay", "mpv"):
            if shutil.which(cmd):
                return cmd
        return None

    def _check_edge_tts(self) -> bool:
        """Checks if edge_tts Python library or CLI is available."""
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return bool(shutil.which("edge-tts"))

    def stop(self):
        """Immediately stops any currently playing speech."""
        with self._lock:
            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=0.5)
                except Exception:
                    try:
                        self.current_process.kill()
                    except Exception:
                        pass
                finally:
                    self.current_process = None

    def speak(self, text: str) -> bool:
        """
        Synthesizes and speaks text synchronously.
        Uses edge-tts if online/installed, otherwise falls back to espeak-ng.
        """
        if not self.enabled or not text:
            return False

        clean = clean_text_for_speech(text)
        if not clean:
            return False

        self.stop()

        # Try edge-tts first for high quality
        if self.has_edge_tts and self.player:
            try:
                success = self._speak_edge_tts(clean)
                if success:
                    return True
            except Exception:
                pass

        # Offline fallback: espeak-ng / espeak
        if self.has_espeak:
            try:
                return self._speak_espeak(clean)
            except Exception:
                pass

        return False

    def _speak_edge_tts(self, text: str) -> bool:
        """Generates MP3 using edge-tts and plays via detected system player."""
        import edge_tts

        filename = f"speech_{abs(hash(text)) % 100000}.mp3"
        out_path = os.path.join(CACHE_DIR, filename)

        async def _gen():
            comm = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
            await comm.save(out_path)

        asyncio.run(_gen())

        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            return False

        # Play audio via player
        play_cmd = []
        if self.player == "ffplay":
            play_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", out_path]
        elif self.player == "paplay":
            play_cmd = ["paplay", out_path]
        elif self.player == "mpv":
            play_cmd = ["mpv", "--no-video", "--really-quiet", out_path]
        else:
            play_cmd = ["aplay", "-q", out_path]

        with self._lock:
            self.current_process = subprocess.Popen(
                play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        self.current_process.wait()
        with self._lock:
            self.current_process = None

        return True

    def _speak_espeak(self, text: str) -> bool:
        """Offline fallback using espeak-ng with sweet anime-pitched female voice."""
        espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        if not espeak_bin:
            return False

        # Use female voice modifier with raised pitch and pleasant tempo
        cmd = [espeak_bin, "-v", "en+f3", "-p", "78", "-s", "155", text]

        with self._lock:
            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        self.current_process.wait()
        with self._lock:
            self.current_process = None

        return True

    def speak_async(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_done: Optional[Callable[[bool], None]] = None,
    ) -> threading.Thread:
        """
        Asynchronously speaks the text in a background daemon thread.
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
                ok = self.speak(text)
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


# Singleton instance accessor
_global_tts_engine: Optional[TTSEngine] = None


def get_tts_engine(voice: str = DEFAULT_VOICE, enabled: bool = True) -> TTSEngine:
    """Returns the singleton TTSEngine instance."""
    global _global_tts_engine
    if _global_tts_engine is None:
        _global_tts_engine = TTSEngine(voice=voice, enabled=enabled)
    return _global_tts_engine
