# ✨ ✿ Princess Mia ✿ ✨
### Desktop AI Companion & Study Buddy

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-pink.svg)](LICENSE)
[![Tests: 162 Passed](https://img.shields.io/badge/Tests-162%20Passed%20(100%25)-brightgreen.svg)]()
[![Local SLM: Qwen3--4B](https://img.shields.io/badge/SLM-Qwen3--4B%20(Ollama)-purple.svg)]()
[![Local STT: faster--whisper](https://img.shields.io/badge/STT-faster--whisper%20(CPU%20INT8)-orange.svg)]()

Princess Mia is an interactive, autonomous Desktop AI Companion, study buddy, and conversation partner built with a custom retro pixel-art rendering engine, local generative intelligence, natural emotional voice synthesis, and local microphone speech recognition.

The entire system runs **100% locally and offline without paid cloud APIs, tokens, or external network subscriptions**.

---

## 🌟 Key Features

### 🌸 1. Retro Pixel Sprite & Dynamic Canvas Engine
- **47×40 Procedural Pixel Grid**: Animated character sprite rendered in pure Python/Tkinter canvas.
- **Expressive Facial States**: Natural blinking, blushing (`FACE_BLUSH`), excited joy (`FACE_EXCITED`), gentle sleeping (`FACE_SLEEPING`), kissing (`FACE_KISS`), and solemn quiet reaction (`FACE_SAD`).
- **Smooth Actions & Physics**: Jump physics with parabolic gravity, full 360° rotational twirl transforms, celebratory confetti bursts, and waving arm poses.
- **Interactive Atmospheric Scenes**:
  - *Cozy Bedroom* (Warm interior ambient lighting)
  - *Cherry Blossom* (Drifting sakura petals with wind turbulence)
  - *Starlit Night* (Twinkling stars and shooting star meteors)
  - *Sunset Beach* (Animated rolling ocean waves and sun glow)
  - *Rooftop Night* (City skyline silhouette and lunar glow)

### 🧠 2. Local Generative SLM (`local_llm.py`)
- **Model**: `qwen3:4b-instruct-2507-q4_K_M` hosted locally via Ollama.
- **Hardware Acceleration**: Runs on local NVIDIA RTX 4050 Laptop GPU (cuBLAS/CUDA) with graceful CPU fallback.
- **Persistent Conversational Memory**: 8,192-token sliding context window stored in SQLite ([companion_db.py](companion_db.py)), retrieving user facts, study milestones, and relationship progression across sessions.
- **Emotional Boundary Handling**: Distinguishes user scolding/hurtful words from general conversation, reacting with sincere emotional vulnerability rather than toxic cheerfulness.

### 🎙️ 3. Natural, Emotionally Expressive Voice Engine (`speech_engine.py`)
- **Original Anime-Inspired Voice Identity**: Youthful adult female voice with clear articulation, subtle breathiness, and expressive intonation.
- **8 Dynamic Emotional Voice Profiles**:
  - **`DEFAULT_FEMALE`**: Warm, conversational, clear articulation.
  - **`TSUNDERE`**: Defensive, flustered, sharper consonants, quick tempo.
  - **`NATURAL_FIRM_FEMALE`**: Grounded, serious, deliberate pacing, lower register.
  - **`BRIGHT_FEMALE`**: Lively, energetic, enthusiastic pitch modulation.
  - **`SOFT_FEMALE`**: Soft volume, slower pace, vulnerable emotional gravity.
  - **`WARM_FEMALE`**: Gentle, tender, caring affection.
  - **`CALM_FEMALE`**: Measured, reflective tone for explaining complex topics.
  - **`PLAYFUL_FEMALE`**: Spirited, teasing, cheerful anime bounce.
- **Intelligent Emotion Routing**: Separates user input emotion from Mia's own delivery.
- **Dual-Tier Offline Resilience**: Studio-grade neural synthesis via `edge-tts` with 100% offline fallback via `espeak-ng`.

### 🎧 4. Local Microphone Speech Recognition (`speech_input.py`)
- **Engine**: `faster-whisper` running on CPU with INT8 quantization:
  - **Latency**: ~$285\text{ ms}$ transcription latency ($18.6\times$ real-time).
  - **Memory Footprint**: Only ~$158\text{ MB}$ RAM, **$0\text{ MB}$ GPU VRAM impact**, avoiding any VRAM conflict with the 4B SLM on the 6 GB RTX 4050 GPU.
- **Dynamic Energy-Adaptive VAD**: Calibrates ambient room noise and automatically detects speech onset and trailing silence ($1.5\text{ s}$ timeout) for automatic turn completion.
- **PipeWire & ALSA Integration**: Native device enumeration and real-time audio capture.

### 💬 5. WhatsApp-Style Side Chat & Two-Way Hands-Free Mode
- **Collapsible Chat Drawer**: Dedicated messaging stream displaying timestamps and distinct chat bubbles for You and Mia.
- **Push-to-Talk (`🎙️`)**: Click to speak, animated recording timer, and instant transcription.
- **`⚡ Auto-Send` Mode**: When enabled, completed speech is automatically sent to Mia without manual confirmation.
- **`🗣️ Two-Way Voice Mode`**: Continuous conversational turn taking:
  1. You speak to Mia $\rightarrow$ Transcribed via `faster-whisper`.
  2. Mia generates reply via local Qwen3-4B SLM.
  3. Mia speaks aloud in her emotional voice profile.
  4. Once Mia finishes speaking, after a natural $650\text{ ms}$ pause, the microphone automatically opens again for your next turn!
- **Data Privacy & Deletion**: One-click `🗑 Delete` button wipes conversation records from both the visual screen and SQLite interaction tables while preserving study stats.

### 📚 6. Pomodoro Focus Timer & Study Buddy
- Configurable study sessions (15, 25, 45, 60 minutes) across subjects (*Coding*, *Math*, *Physics*, *Reading*, *General*).
- Persistent study streak tracking and session logging.
- Animated cheering and celebratory chimes on timer completion.

---

## 🏗️ Architecture Blueprint

```
                      ┌────────────────────────────────────────┐
                      │              USER INPUT                │
                      │  (Text Entry / Laptop Microphone / CLI)│
                      └───────────────────┬────────────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
                   ▼ (Voice Input)                               ▼ (Text Input)
    ┌─────────────────────────────┐               ┌─────────────────────────────┐
    │       speech_input.py       │               │        pixel_girl.py        │
    │  - PipeWire / ALSA capture  │               │  - Main GUI window          │
    │  - Energy-based VAD         │               │  - WhatsApp side drawer     │
    │  - faster-whisper (CPU INT8)│               └──────────────┬──────────────┘
    └──────────────┬──────────────┘                              │
                   │ (Transcribed Text)                          │
                   └──────────────────────┬──────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │          dialogue_engine.py            │
                      │  - Scold detection & boundary check    │
                      │  - ML intent & emotion integration     │
                      │  - Sliding context window assembly     │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │              local_llm.py              │
                      │  - Qwen3-4B SLM via Ollama (CUDA)      │
                      │  - Personality & study companion prompt│
                      │  - RTX 4050 Laptop GPU (4.1 GB VRAM)   │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │            speech_engine.py            │
                      │  - 8 Emotional Voice Profiles          │
                      │  - Emotion-to-Voice Routing            │
                      │  - edge-tts neural prosody + espeak-ng │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │              OUTPUT STAGE              │
                      │  - Canvas Sprite Animations            │
                      │  - Dynamic Overhead Speech Cloud       │
                      │  - Side Chat Drawer Message Bubble     │
                      │  - Non-blocking Audio Playback (ffplay)│
                      └────────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Linux** (Fedora, Ubuntu, Debian, Arch)
- **Python 3.10+** (tested up to Python 3.14)
- **Audio Tools**: `ffplay` (from ffmpeg), `espeak-ng`
  ```bash
  # Fedora
  sudo dnf install ffmpeg-free espeak-ng portaudio-devel
  # Ubuntu / Debian
  sudo apt install ffmpeg espeak-ng portaudio19-dev
  ```
- **Local Model Runtime (Ollama)**:
  ```bash
  # Install and pull the primary 4B model
  ollama pull qwen3:4b-instruct-2507-q4_K_M
  ollama serve
  ```

### 2. Installation
```bash
git clone https://github.com/devanshbaghel18/pixi.git
cd pixi
pip install -r requirements.txt
```

### 3. Launching Princess Mia
```bash
# Launch interactive desktop companion
python3 pixel_girl.py

# Or use the launcher script
./scripts/run_app.sh

# Or run in lightweight terminal mode
python3 pixel_girl.py --terminal
```

---

## 🎛️ Keyboard & UI Shortcuts

| Control | Action |
|---|---|
| **`Enter`** | Send message to Mia |
| **`Esc`** | Exit companion cleanly (stops all active audio processes) |
| **`💬 Chat: ON / OFF`** | Toggle WhatsApp-style side drawer |
| **`🎙️`** | Push-to-Talk: click to start recording, click again to stop |
| **`⚡ Auto: ON / OFF`** | Automatically send transcribed speech without manual review |
| **`🗣️ 2-Way: ON / OFF`** | Hands-free continuous Two-Way Voice Conversation mode |
| **`🔊 Voice: ON / OFF`** | Toggle Mia's speech voice audio |
| **`🔔 Chime: ON / OFF`** | Toggle retro 8-bit chime sound effects |
| **`🗑 Delete`** | Wipe conversation records from UI and SQLite database |

---

## 🧪 Testing & Verification

All **162 automated unit and integration tests** pass:

```bash
# Run the complete test suite
python3 run_tests.py

# Or run with unittest
python3 -m unittest discover -s . -p "test_*.py"
```

### Test Coverage Breakdown
- **Frontend UI & Canvas**: Themes, scenes, jump/twirl physics, speech cloud, chat drawer, 2-way mode.
- **Dialogue Engine**: Intent classification, emotional boundaries, scold handling, context pruning.
- **Generative SLM**: Open-domain conversations, quantum physics, coding, follow-up memory.
- **Speech Engine**: 8 voice profiles, emotion-to-voice routing, offline fallback, text cleaning.
- **Speech Input**: Device enumeration, energy-based VAD, faster-whisper CPU INT8 transcription.

---

## 📂 Project Structure

```
cool/
├── pixel_girl.py              # Main desktop GUI application, sprite animation & chat drawer
├── dialogue_engine.py         # Conversational routing, boundary checks & context logic
├── local_llm.py               # Ollama local generative SLM client (Qwen3-4B)
├── speech_engine.py           # 8 emotional voice profiles, neural synthesis & offline fallback
├── speech_input.py            # Microphone capture, VAD silence detection & faster-whisper
├── companion_db.py            # SQLite schema, interactions, affection tiers & study stats
├── ml_classifier.py           # Auxiliary TF-IDF intent & emotion classifier
├── sound_synth.py             # Procedural 8-bit retro audio chime synthesizer
├── tts_engine.py              # Auxiliary TTS utility module
├── smoke_test_real_model.py   # Live model benchmark and hardware evaluation script
├── run_tests.py               # Unified test runner with colorized summary output
├── test_frontend.py           # GUI, chat drawer, voice and microphone tests
├── test_dialogue.py           # Dialogue engine and emotional boundary tests
├── test_generative_dialogue.py# 13 open-domain conversation scenario tests
├── test_db.py                 # SQLite database and interaction persistence tests
├── test_local_llm.py          # Local SLM context window and prompt injection tests
├── test_ml_classifier.py      # ML classifier calibration and active learning tests
├── test_sound_synth.py        # 8-bit sound synthesizer tests
├── scripts/
│   ├── run_app.sh             # Desktop application launcher
│   └── benchmark_voices.py    # Voice profile audio generator & benchmark utility
├── pyproject.toml             # Standard PEP 517/621 packaging metadata
├── requirements.txt           # Production dependencies
├── AGENTS.md                  # Multi-agent engineering rules and roster
└── README.md                  # System documentation and user guide
```

---

## 📄 License
This project is licensed under the MIT License.
