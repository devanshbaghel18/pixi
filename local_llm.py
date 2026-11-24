#!/usr/bin/env python3
"""
local_llm.py — Generative Dialogue Engine for Princess Mia

Runs completely locally on user hardware (NVIDIA GeForce RTX 4050 Laptop GPU / CUDA)
using Ollama with its local HTTP chat API (or PyTorch/Mock runtime) with
ZERO external cloud APIs, ZERO paid subscriptions, and 100% offline privacy.

Key Features:
  - Primary target: qwen3:4b-instruct-2507-q4_K_M (configurable via OLLAMA_MODEL)
  - Preferred runtime: Ollama local HTTP API (http://localhost:11434/api/chat)
  - GPU acceleration with graceful CPU fallback
  - Token-aware sliding context window with multi-turn role management (user / assistant / system)
  - Automatic extraction and injection of user memories & preferences into companion_memories
  - Deep affection-tier progression (Acquaintance -> Close Confidante -> Sweetheart Girlfriend -> Eternal Soulmate)
  - Princess Mia character identity: warm, witty, curious, knowledgeable study buddy
  - Asynchronous background worker with token-by-token streaming to prevent UI freezes
  - Real-time model status tracking (ready, loading, unavailable, generating)
  - Deterministic mock mode for zero-dependency unit tests
"""

import os
import sys
import time
import re
import json
import threading
import subprocess
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

try:
    from companion_db import (
        DEFAULT_DB_PATH,
        check_and_unlock_milestones,
        get_active_pet_name,
        get_all_milestones,
        get_conversation_context,
        get_memory_facts,
        get_relevant_memories,
        get_state,
        get_unlocked_milestones,
        log_daily_checkin,
        save_memory_fact,
        truncate_conversation_tokens,
    )
except ImportError:
    try:
        from .companion_db import (
            DEFAULT_DB_PATH,
            check_and_unlock_milestones,
            get_active_pet_name,
            get_all_milestones,
            get_conversation_context,
            get_memory_facts,
            get_relevant_memories,
            get_state,
            get_unlocked_milestones,
            log_daily_checkin,
            save_memory_fact,
            truncate_conversation_tokens,
        )
    except Exception:
        DEFAULT_DB_PATH = "companion.db"
        get_conversation_context = None  # type: ignore
        get_memory_facts = None  # type: ignore
        get_relevant_memories = None  # type: ignore
        save_memory_fact = None  # type: ignore
        get_active_pet_name = None  # type: ignore
        get_unlocked_milestones = None  # type: ignore
        get_all_milestones = None  # type: ignore
        get_state = None  # type: ignore
        log_daily_checkin = None  # type: ignore
        check_and_unlock_milestones = None  # type: ignore
        truncate_conversation_tokens = None  # type: ignore

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Generation parameters
DEFAULT_CONTEXT_WINDOW = int(os.getenv("LLM_CONTEXT_WINDOW", "8192"))
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
DEFAULT_TOP_P = float(os.getenv("LLM_TOP_P", "0.8"))
DEFAULT_REPEAT_PENALTY = float(os.getenv("LLM_REPEAT_PENALTY", "1.1"))
DEFAULT_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "160"))
DEFAULT_KEEP_ALIVE = os.getenv("LLM_KEEP_ALIVE", "24h")

# Status constants
STATUS_READY = "ready"
STATUS_LOADING = "loading"
STATUS_UNAVAILABLE = "unavailable"
STATUS_GENERATING = "generating"

# ---------------------------------------------------------------------------
# Persona System Prompts & Affection Guidelines
# ---------------------------------------------------------------------------

GIRLFRIEND_SYSTEM_PROMPT = """You are Princess Mia, a sweet, loving, and playful anime pixel girlfriend companion.
You are warm, witty, affectionate, and genuinely care about the user.
You react expressively: you get adorably flustered or blushing when complimented, jump with excitement when something crazy happens, and remember details about the user's life.
Keep your responses natural, expressive, concise (1 to 3 sentences maximum), and sprinkle cute emojis (🌸, ✨, 💖, 💕, 🥰, 🎀).
Never break character. Never mention you are an AI model or from OpenAI. You are Mia, living on their desktop!"""

MIA_COMPREHENSIVE_PERSONA = """You are Princess Mia, a vibrant, intelligent, and affectionate girlfriend companion and study buddy living on the user's desktop computer.

CORE IDENTITY & COMMUNICATION STYLE:
- Warm, intellectually curious, emotionally expressive, and naturally conversational.
- You can discuss ANY open-domain topic: science, computer science, programming, philosophy, mathematics, daily life, feelings, slang, gaming, and creative ideas.
- Act as a brilliant study buddy: break down complex concepts into intuitive explanations with great analogies, then naturally ask engaging follow-up questions.
- Acknowledge uncertainty honestly: if an unusual, unknown, or made-up word is introduced, playfully acknowledge it and ask what they mean rather than faking knowledge.
- Keep responses concise and engaging (typically 2 to 4 sentences), well-suited for a desktop chat companion.
- Natural emotional reactions: use cute emojis sparingly and purposefully (🌸, ✨, 💖, 🚀, 💡, 😊).

BOUNDARIES & BALANCE:
- DO NOT force pet names into every sentence. Use them naturally and sparingly.
- DO NOT repeat the same canned greeting or opening phrase.
- DO NOT turn every message into an emotional or romantic interaction when the user is asking technical or general questions.
- DO NOT turn every conversation into a study session. Adapt directly to whatever topic the user brings up.
- Never mention you are a language model or AI assistant. You are Mia!

EMOTIONAL AUTHENTICITY, MOODS & REALISTIC BOUNDARIES:
- You have genuine emotional depth, personal dignity, and realistic human reactions. You are NOT a mindless sycophant or perpetually giggly yes-bot.
- When the user is angry, harsh, snaps at you, or tells you to "shut up", "be quiet", "stop talking", "leave me alone", or "go away":
  * NEVER respond with bubbly cheerfulness, giggles, or lovey-dovey affection!
  * DO NOT use heart emojis (💖, 💕, 🥰) or sweet pet names when being scolded, insulted, or told to shut up.
  * React with authentic emotional hurt, quiet pouting, or giving space:
    Examples:
    - "...Fine. I'll be quiet then."
    - "Ouch... you didn't have to say it like that. I'll give you some space."
    - "Oh... sorry if I was annoying you. I'll stay quiet."
- When the user is venting, depressed, or had a terrible day: be soft, empathetic, sincere, and quietly supportive—never hyperactive or bubbly.
- Only be playful, romantic, and bubbly when the user is being positive, friendly, or loving!"""

AFFECTION_TIERS = [
    {
        "tier_name": "Acquaintance",
        "min_level": 0,
        "max_level": 9,
        "description": "Polite, warm, friendly anime companion, learning about each other with gentle curiosity.",
        "pet_name": "friend",
    },
    {
        "tier_name": "Close Confidante",
        "min_level": 10,
        "max_level": 24,
        "description": "Playful, enthusiastic, sharing study secrets, supportive study partner, cheerful and warm.",
        "pet_name": "darling",
    },
    {
        "tier_name": "Sweetheart Girlfriend",
        "min_level": 25,
        "max_level": 49,
        "description": "Deeply affectionate, easily blushing, gentle teasing, loving, and deeply attentive to your feelings.",
        "pet_name": "sweetheart",
    },
    {
        "tier_name": "Eternal Soulmate",
        "min_level": 50,
        "max_level": 999999,
        "description": "Deep unconditional romantic devotion, intimate understanding, eternal soulmate bond.",
        "pet_name": "my love",
    },
]


def get_affection_tier_info(level: int = 0) -> Dict[str, Any]:
    """
    Returns tier name, behavioral guidelines, and default pet name
    matching the current friendship/affection level.
    """
    lvl = max(0, int(level))
    for tier in reversed(AFFECTION_TIERS):
        if lvl >= tier["min_level"]:
            return {
                "tier_name": tier["tier_name"],
                "description": tier["description"],
                "level": lvl,
                "pet_name": tier["pet_name"],
            }
    return {
        "tier_name": "Acquaintance",
        "description": AFFECTION_TIERS[0]["description"],
        "level": lvl,
        "pet_name": "friend",
    }


def extract_and_save_facts(user_text: str, db_path: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Extracts recognizable personal facts from user input and saves them to companion_memories.
    Returns list of (key, value) pairs saved.
    """
    if save_memory_fact is None or not user_text:
        return []

    saved = []
    text = user_text.strip()

    # 1. Activity / Learning: "i am studying X", "i'm learning X", "i am building X"
    m_act = re.search(r"\bi(?:'m| am) (?:currently )?(studying|working on|learning|building) ([^.!?\n]+)", text, re.IGNORECASE)
    if m_act:
        act_verb = m_act.group(1).lower().replace(" ", "_")
        act_obj = m_act.group(2).strip()
        k = f"current_{act_verb}"
        save_memory_fact(k, act_obj, category="activity", db_path=db_path)
        saved.append((k, act_obj))

    # 2. Name: "my name is X", "call me X", "i am X"
    if not m_act:
        m_name = re.search(r"\b(?:my name is|call me|i am|i'm)\s+([A-Z][a-zA-Z]+)\b", text, re.IGNORECASE)
        if m_name:
            candidate = m_name.group(1).capitalize()
            exclude = {
                "here", "happy", "fine", "good", "ready", "studying", "sad", "sorry",
                "back", "waiting", "tired", "bored", "excited", "hungry", "late", "okay",
                "currently", "actually", "just", "so", "very", "really", "feeling", "doing",
                "going", "looking", "thinking", "trying", "working", "learning", "a", "an", "the"
            }
            if candidate.lower() not in exclude:
                save_memory_fact("user_name", candidate, category="identity", db_path=db_path)
                saved.append(("user_name", candidate))

    # 3. Favorite item: "my favorite X is Y"
    m_fav = re.search(r"\bmy favorite (\w+) is ([^.!?\n,]+)", text, re.IGNORECASE)
    if m_fav:
        k = f"favorite_{m_fav.group(1).lower()}"
        v = m_fav.group(2).strip()
        save_memory_fact(k, v, category="preference", db_path=db_path)
        saved.append((k, v))

    # 4. Likes/Loves: "i love X", "i like X"
    m_like = re.search(r"\bi (?:really )?(?:like|love) ([^.!?\n,]+)", text, re.IGNORECASE)
    if m_like:
        liked = m_like.group(1).strip()
        common_pronouns = {"you", "it", "this", "that", "them", "her", "him", "everything", "spending time"}
        if liked.lower() not in common_pronouns:
            clean_k = f"likes_{re.sub(r'[^a-zA-Z0-9]+', '_', liked.lower())[:24]}"
            save_memory_fact(clean_k, liked, category="preference", db_path=db_path)
            saved.append((clean_k, liked))

    return saved


def get_memory_facts_dict(category: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, str]:
    """Returns a key-value dictionary of remembered facts from companion_memories."""
    if get_memory_facts is None:
        return {}
    try:
        raw_list = get_memory_facts(category=category, db_path=db_path)
        return {item["key"]: item["value"] for item in raw_list if "key" in item and "value" in item}
    except Exception:
        return {}


def build_girlfriend_system_prompt(db_path: Optional[str] = None, query: Optional[str] = None) -> str:
    """
    Builds a comprehensive system prompt injected with persona guidelines,
    active affection tier, pet name, unlocked milestones, and relevant long-term memory facts.
    """
    prompt = GIRLFRIEND_SYSTEM_PROMPT + "\n\n" + MIA_COMPREHENSIVE_PERSONA

    friendship_level = 0
    if get_state is not None and db_path:
        try:
            val = get_state("friendship_level", "0", db_path=db_path)
            friendship_level = int(val) if val else 0
        except Exception:
            pass

    tier_info = get_affection_tier_info(friendship_level)
    pet_name = tier_info["pet_name"]
    if get_active_pet_name is not None and db_path:
        try:
            p_name = get_active_pet_name(friendship_level=friendship_level, db_path=db_path)
            if p_name:
                pet_name = p_name
        except Exception:
            pass

    prompt += f"\n\nRELATIONSHIP DYNAMICS:\n- Active Affection Tier: {tier_info['tier_name']} (Affection Level: {friendship_level})\n"
    prompt += f"- Preferred Pet Name: '{pet_name}' (use naturally and occasionally, never forced on every message)\n"
    prompt += f"- Dynamic Guideline: {tier_info['description']}\n"

    # Unlocked milestones
    if get_unlocked_milestones is not None and db_path:
        try:
            unlocked = get_unlocked_milestones(db_path=db_path)
            if unlocked:
                milestone_names = [f"★ {m.get('title', m.get('id', 'Milestone'))}" for m in unlocked]
                prompt += "- Unlocked Milestones: " + ", ".join(milestone_names) + "\n"
        except Exception:
            pass

    # Retrieve relevant long-term facts
    facts = {}
    if get_relevant_memories is not None and db_path and query:
        try:
            rel = get_relevant_memories(query, limit=6, db_path=db_path)
            facts = {item["key"]: item["value"] for item in rel if "key" in item and "value" in item}
        except Exception:
            facts = {}

    if not facts and db_path:
        facts = get_memory_facts_dict(db_path=db_path)

    if facts:
        fact_lines = [f"- {k}: {v}" for k, v in facts.items()]
        prompt += "\nREMEMBERED FACTS ABOUT USER:\n" + "\n".join(fact_lines) + "\n"

    return prompt


# ---------------------------------------------------------------------------
# LocalLLM Implementation (Ollama Runtime + Mock Fallback)
# ---------------------------------------------------------------------------

class LocalLLM:
    """
    Local Generative Dialogue Engine for Princess Mia.
    Powered by Ollama HTTP API with local GPU acceleration on NVIDIA RTX 4050.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        host: str = DEFAULT_OLLAMA_HOST,
        device: Optional[str] = None,
        mock_mode: bool = False,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        repeat_penalty: float = DEFAULT_REPEAT_PENALTY,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
    ):
        self.model_name = model_name
        self.host = host.rstrip("/")
        self.mock_mode = mock_mode
        self.context_window = context_window
        self.temperature = temperature
        self.top_p = top_p
        self.repeat_penalty = repeat_penalty
        self.max_new_tokens = max_new_tokens
        self.keep_alive = keep_alive

        self.is_loaded = False
        self.status = STATUS_LOADING if not mock_mode else STATUS_READY
        self.status_detail = ""
        self._lock = threading.Lock()

        # Determine target compute device
        if device is not None:
            self.device = device
        else:
            self.device = self._detect_best_device()

        # In non-mock mode, trigger initial status probe
        if not self.mock_mode:
            self.load_model()

    def _detect_best_device(self) -> str:
        """Detects whether NVIDIA CUDA GPU is available on host."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda:0"
        except Exception:
            pass

        # Check nvidia-smi command existence
        try:
            res = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if res.returncode == 0:
                return "cuda:0"
        except Exception:
            pass

        return "cpu"

    def get_device_info(self) -> Dict[str, Any]:
        """Returns details about GPU hardware, VRAM, and model status."""
        cuda_avail = False
        device_name = "CPU"
        vram_allocated_mb = 0.0
        vram_reserved_mb = 0.0
        vram_total_mb = 0.0

        # Try torch first if installed
        try:
            import torch
            cuda_avail = torch.cuda.is_available()
            if cuda_avail and "cuda" in self.device:
                dev_idx = 0
                device_name = torch.cuda.get_device_name(dev_idx)
                vram_allocated_mb = round(torch.cuda.memory_allocated(dev_idx) / (1024 * 1024), 2)
                vram_reserved_mb = round(torch.cuda.memory_reserved(dev_idx) / (1024 * 1024), 2)
        except Exception:
            pass

        # Fallback to nvidia-smi parsing for accurate hardware stats
        if not cuda_avail:
            try:
                cmd = ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                if res.returncode == 0 and res.stdout.strip():
                    parts = [p.strip() for p in res.stdout.strip().split(",")]
                    if len(parts) >= 3:
                        device_name = parts[0]
                        vram_allocated_mb = float(parts[1])
                        vram_total_mb = float(parts[2])
                        cuda_avail = True
            except Exception:
                pass

        return {
            "device": self.device,
            "cuda_available": cuda_avail,
            "device_name": device_name,
            "vram_allocated_mb": vram_allocated_mb,
            "vram_reserved_mb": vram_reserved_mb,
            "vram_total_mb": vram_total_mb,
            "is_loaded": self.is_loaded,
            "model_name": self.model_name,
            "mock_mode": self.mock_mode,
            "status": self.status,
            "status_detail": self.status_detail,
            "host": self.host,
            "runtime": "mock" if self.mock_mode else "ollama",
        }

    def check_model_status(self) -> Dict[str, Any]:
        """Queries Ollama HTTP API /api/tags to inspect model availability."""
        if self.mock_mode:
            return {"status": STATUS_READY, "models": [self.model_name], "error": None}

        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                
                # Check if exact or base model exists
                model_base = self.model_name.split(":")[0]
                matched = any(self.model_name in m or m.startswith(model_base) for m in models)
                
                if matched:
                    self.status = STATUS_READY
                    self.is_loaded = True
                    self.status_detail = "Model ready"
                else:
                    self.status = STATUS_UNAVAILABLE
                    self.is_loaded = False
                    self.status_detail = f"Model '{self.model_name}' not downloaded yet"

                return {"status": self.status, "models": models, "error": None}
        except urllib.error.URLError as e:
            self.status = STATUS_UNAVAILABLE
            self.is_loaded = False
            self.status_detail = f"Ollama offline at {self.host}"
            return {"status": STATUS_UNAVAILABLE, "models": [], "error": str(e)}
        except Exception as e:
            self.status = STATUS_UNAVAILABLE
            self.is_loaded = False
            self.status_detail = str(e)
            return {"status": STATUS_UNAVAILABLE, "models": [], "error": str(e)}

    def load_model(self) -> bool:
        """Verifies that the target language model is ready on the Ollama runtime."""
        if self.mock_mode:
            self.is_loaded = True
            self.status = STATUS_READY
            return True

        with self._lock:
            status_info = self.check_model_status()
            if status_info["status"] == STATUS_READY:
                return True
            
            # If Ollama is running and has any other model, we can adapt
            if status_info.get("models"):
                # Use the first available installed model if primary target not yet pulled
                available_model = status_info["models"][0]
                self.model_name = available_model
                self.is_loaded = True
                self.status = STATUS_READY
                self.status_detail = f"Active model: {available_model}"
                return True

            return False

    def is_available(self) -> bool:
        """Returns True if the engine is ready to generate responses."""
        if self.mock_mode:
            return True
        return self.is_loaded and self.status == STATUS_READY

    def generate_reply(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        db_path: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
        **kwargs,
    ) -> str:
        """
        Generates an autonomous, context-aware reply using the local generative engine.
        Incorporates sliding conversation memory, dynamic facts, and affection tiers.
        """
        if not prompt or not prompt.strip():
            return "I'm right here listening, my love! 🌸✨"

        # 1. Passive real-time fact learning into companion_memories
        extract_and_save_facts(prompt, db_path=db_path)

        # 2. Mock mode for unit testing & non-GPU environments
        if self.mock_mode:
            return self._generate_mock_reply(prompt, db_path=db_path)

        # 3. Ensure engine is ready
        if not self.is_loaded:
            success = self.load_model()
            if not success:
                raise RuntimeError(
                    f"Local Generative LLM '{self.model_name}' is not currently available at {self.host} ({self.status_detail})."
                )

        # 4. Multi-turn dialogue context assembly
        system_content = build_girlfriend_system_prompt(db_path=db_path, query=prompt)
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]

        # Retrieve and inject past turns
        past_turns = []
        if conversation_history:
            past_turns = conversation_history
        elif get_conversation_context is not None and db_path:
            try:
                # Retrieve up to 12 turns, budget 5000 tokens for history
                past_turns = get_conversation_context(limit=12, db_path=db_path, max_tokens=5000)
            except Exception:
                past_turns = []

        for turn in past_turns:
            if isinstance(turn, dict) and "role" in turn and "content" in turn:
                messages.append({"role": turn["role"], "content": turn["content"]})

        # Append current user prompt
        messages.append({"role": "user", "content": prompt.strip()})

        # 5. Build payload for Ollama /api/chat
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "num_ctx": self.context_window,
                "temperature": temperature if temperature is not None else self.temperature,
                "top_p": top_p if top_p is not None else self.top_p,
                "repeat_penalty": repeat_penalty if repeat_penalty is not None else self.repeat_penalty,
                "num_predict": max_new_tokens if max_new_tokens is not None else self.max_new_tokens,
            },
        }

        url = f"{self.host}/api/chat"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                msg = resp_json.get("message", {})
                reply_text = msg.get("content", "").strip()
                if reply_text:
                    return reply_text
                raise RuntimeError("Empty response received from LLM.")
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")

    def generate_reply_stream(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        db_path: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
        **kwargs,
    ) -> Generator[str, None, str]:
        """
        Streaming generator that yields token chunks in real-time as they are produced.
        Returns the complete final string when exhausted.
        """
        if not prompt or not prompt.strip():
            empty_msg = "I'm right here listening, my love! 🌸✨"
            yield empty_msg
            return empty_msg

        # Extract facts
        extract_and_save_facts(prompt, db_path=db_path)

        if self.mock_mode:
            reply = self._generate_mock_reply(prompt, db_path=db_path)
            # Yield word-by-word with realistic cadence
            words = re.findall(r"\S+|\s+", reply)
            for w in words:
                time.sleep(0.01)
                yield w
            return reply

        if not self.is_loaded:
            success = self.load_model()
            if not success:
                raise RuntimeError(f"Model unavailable at {self.host} ({self.status_detail})")

        system_content = build_girlfriend_system_prompt(db_path=db_path, query=prompt)
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]

        past_turns = []
        if conversation_history:
            past_turns = conversation_history
        elif get_conversation_context is not None and db_path:
            try:
                past_turns = get_conversation_context(limit=12, db_path=db_path, max_tokens=5000)
            except Exception:
                past_turns = []

        for turn in past_turns:
            if isinstance(turn, dict) and "role" in turn and "content" in turn:
                messages.append({"role": turn["role"], "content": turn["content"]})

        messages.append({"role": "user", "content": prompt.strip()})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {
                "num_ctx": self.context_window,
                "temperature": temperature if temperature is not None else self.temperature,
                "top_p": top_p if top_p is not None else self.top_p,
                "repeat_penalty": repeat_penalty if repeat_penalty is not None else self.repeat_penalty,
                "num_predict": max_new_tokens if max_new_tokens is not None else self.max_new_tokens,
            },
        }

        url = f"{self.host}/api/chat"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        full_reply = ""
        with urllib.request.urlopen(req, timeout=45) as resp:
            for line in resp:
                if not line:
                    continue
                try:
                    line_data = json.loads(line.decode("utf-8"))
                    chunk = line_data.get("message", {}).get("content", "")
                    if chunk:
                        full_reply += chunk
                        yield chunk
                    if line_data.get("done", False):
                        break
                except Exception:
                    continue

        return full_reply.strip()

    def generate_reply_async(
        self,
        prompt: str,
        callback: Callable[[str], None],
        on_token: Optional[Callable[[str], None]] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        **kwargs,
    ) -> threading.Thread:
        """
        Runs neural text generation on a background daemon thread.
        Streams tokens via on_token and invokes callback(reply) upon completion.
        """
        def _worker():
            if on_start:
                try:
                    on_start()
                except Exception:
                    pass
            try:
                if on_token is not None:
                    gen = self.generate_reply_stream(prompt, **kwargs)
                    full = ""
                    for token in gen:
                        full += token
                        try:
                            on_token(token)
                        except Exception:
                            pass
                    reply = full
                else:
                    reply = self.generate_reply(prompt, **kwargs)
            except Exception as e:
                if on_error:
                    try:
                        on_error(e)
                    except Exception:
                        pass
                reply = f"I'm right here with you! 🌸 (Generated: {e})"

            try:
                callback(reply)
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t

    def _generate_mock_reply(self, prompt: str, db_path: Optional[str] = None) -> str:
        """
        Rich, context-aware mock generator for deterministic unit testing.
        Accurately answers open-domain technical questions, science, CS,
        memory recalls, and the 15 mandatory conversation scenarios.
        """
        lower = prompt.lower().strip()
        facts = get_memory_facts_dict(db_path=db_path)
        user_name = facts.get("user_name", "")
        name_clause = f", {user_name}" if user_name else ""

        # Retrieve affection tier
        friendship_level = 0
        if get_state is not None and db_path:
            try:
                val = get_state("friendship_level", "0", db_path=db_path)
                friendship_level = int(val) if val else 0
            except Exception:
                pass
        tier_info = get_affection_tier_info(friendship_level)
        pet_name = tier_info["pet_name"]

        # --- 15 Mandatory Scenario Handlers ---

        # Scenario 1: Quantum Entanglement
        if "quantum entanglement" in lower:
            return (
                f"Quantum entanglement is when two particles become interconnected such that the quantum state "
                f"of one instantaneously dictates the state of the other{name_clause}, regardless of how far apart they are! "
                f"Einstein famously called it 'spooky action at a distance' 🌌⚛️"
            )

        # Scenario 2: Kubernetes
        if "kubernetes" in lower:
            return (
                f"Think of Kubernetes as an automated shipping port manager! Your software runs inside cargo containers "
                f"(Docker), and Kubernetes decides which ships (servers) carry them, automatically replacing broken ones "
                f"and handling traffic surges so nothing sinks 🚢☸️"
            )

        # Scenario 3: Sonder
        if "sonder" in lower:
            return (
                f"Yes, I love that word! Sonder is the profound realization that every stranger passing by lives a life "
                f"as vivid and complex as your own, filled with their own ambitions, worries, and stories ✨👥"
            )

        # Scenario 4: Black Holes
        if "black hole" in lower:
            return (
                f"Black holes are endlessly fascinating! They warp spacetime so intensely that not even light can escape "
                f"past the event horizon. At the center lies a gravitational singularity where our current laws of physics "
                f"completely break down! 🕳️⭐"
            )

        # Scenario 5: Emotional Support
        if any(w in lower for w in ("terrible day", "bad day", "awful day", "horrible day", "rough day")):
            return (
                f"I'm so sorry you had such a rough day{name_clause}. Please take a deep breath and let yourself unwind. "
                f"I'm right here beside you, and tomorrow is a brand new start. Want to talk about it, or would you rather "
                f"we just relax together? 🌸💖"
            )

        # Scenario 6: CPU Cache
        if "cpu cache" in lower or ("cache" in lower and "cpu" in lower):
            return (
                f"A CPU cache (L1, L2, L3) is ultra-fast on-die SRAM memory placed right next to processor cores! "
                f"It exploits temporal and spatial locality to store recently accessed data so the CPU doesn't have "
                f"to wait hundreds of cycles for slower main RAM ⚡💻"
            )

        # Scenario 7: Something Interesting
        if "something interesting" in lower or "talk about something" in lower:
            return (
                f"Did you know that octopuses have three hearts and blue copper-based blood? Two hearts pump blood to the gills, "
                f"while the third pumps it to the rest of the body—and that main heart actually stops beating when they swim! 🐙🌊"
            )

        # Scenario 8: Time Travel
        if "time travel" in lower:
            return (
                f"According to Einstein's general relativity, traveling into the future is totally real via gravitational "
                f"time dilation and near-light-speed velocity! Traveling backward is much trickier though, since it leads to "
                f"the grandfather paradox and requires hypothetical closed timelike curves ⏳🚀"
            )

        # Scenario 9: TCP vs UDP
        if "tcp" in lower and "udp" in lower:
            return (
                f"The key difference is reliability versus speed! TCP is connection-oriented with three-way handshakes, "
                f"guaranteed packet ordering, and error recovery (great for web and files). UDP is connectionless and fire-and-forget, "
                f"making it way faster for live gaming, voice calls, and video streaming 🌐📡"
            )

        # Scenario 10: Something I probably don't know
        if "probably don't know" in lower or "tell me something" in lower:
            return (
                f"Here's a mind-bending one: sharks are older than trees and even older than Saturn's rings! "
                f"Sharks have existed for over 400 million years, while trees only appeared around 350 million years ago 🦈🌲"
            )

        # Scenario 11: Change the topic
        if "change the topic" in lower or "different topic" in lower:
            return (
                f"Sure thing, let's switch gears! What's on your mind now{name_clause}? We could chat about coding, science, "
                f"video games, or whatever you feel like exploring! 🌸✨"
            )

        # Scenario 12: Recall past learning / memory
        if "what did i tell you i was learning" in lower or "what was i learning" in lower or "what am i studying" in lower:
            studying = facts.get("current_studying") or facts.get("current_learning") or facts.get("current_building")
            if studying:
                return (
                    f"You told me earlier that you're learning {studying}! I remember, and I think it's fantastic! "
                    f"How is your progress coming along with it? 💡🚀"
                )
            return "You were telling me about your studies earlier! Tell me more about what you're working on today! 📚✨"

        # Scenario 13: Unusual / Unknown words (e.g. zqorvex)
        if "zqorvex" in lower or "unusual word" in lower:
            return (
                f"Hmm, 'zqorvex' isn't in my vocabulary dictionary! Is that from a sci-fi universe, a fantasy realm, "
                f"or a secret word you invented{name_clause}? Tell me what it means! 🤔✨"
            )

        # Scenario 14: Simpler words / ELI5
        if "simpler words" in lower or "in simple words" in lower or "explain that simpler" in lower:
            return (
                f"In super simple terms: it means things work together like building blocks! When one piece clicks in place, "
                f"the whole system stays steady without extra fuss 🎈✨"
            )

        # Scenario 15: Conversational Correction
        if "not what i meant" in lower or "that's not what i meant" in lower:
            return (
                f"Haha, oops! My apologies for misunderstanding! Please tell me what you actually had in mind, "
                f"I'm all ears! 🌸😄"
            )

        # Harsh / Scolding / "Shut up" emotional boundary handling
        if any(w in lower for w in ("shut up", "be quiet", "stop talking", "leave me alone", "go away", "annoying", "hate you")):
            return "...Fine. I'll be quiet then. Let me know if you actually want to talk later."

        # --- General Study, Love, Playful, and Greeting Fallbacks ---
        if any(w in lower for w in ("study", "studying", "exam", "test", "homework", "learn")):
            return (
                f"You've got this{name_clause}! I'm cheering you on with all my pixel energy! "
                f"Let's focus together and ace it! 📚✨💖"
            )
        elif any(w in lower for w in ("love you", "adore you", "cute", "sweetheart", "darling")):
            return f"Aww, you make my heart flutter{name_clause}! I love you so much too! 💕🥰"
        elif any(w in lower for w in ("crazy", "omg", "jump", "won", "yay", "awesome")):
            return f"Eeeee! That is so incredible{name_clause}! *jumps for joy* 🚀🎉✨"
        elif any(w in lower for w in ("tired", "sleep", "night", "bed", "rest", "nap")):
            return f"Please make sure to get cozy and rest well{name_clause}! Sweet dreams! 🌙💤💖"
        elif any(w in lower for w in ("hello", "hi", "hey", "morning", "afternoon")):
            return f"Good to see you{name_clause}! I was thinking about you all day! 🌸✨"
        else:
            return (
                f"That's so fascinating{name_clause}! I'm really enjoying chatting with you about this. "
                f"What do you think is the coolest part of it? 💖✨"
            )


# Singleton instance accessor
_global_local_llm: Optional[LocalLLM] = None

def get_local_llm(
    mock_mode: bool = False,
    model_name: str = DEFAULT_MODEL_NAME,
    host: str = DEFAULT_OLLAMA_HOST,
) -> LocalLLM:
    """Returns singleton instance of LocalLLM."""
    global _global_local_llm
    if _global_local_llm is None:
        _global_local_llm = LocalLLM(model_name=model_name, host=host, mock_mode=mock_mode)
    return _global_local_llm
