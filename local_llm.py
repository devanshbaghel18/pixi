#!/usr/bin/env python3
"""
local_llm.py — Local Neural Language Model Dialogue Pipeline for Princess Mia

Runs completely locally on user hardware (NVIDIA GeForce RTX 4050 Laptop GPU / CUDA)
with ZERO external APIs, ZERO cloud tracking, and 100% offline privacy.

Features:
  - PyTorch + CUDA acceleration on NVIDIA RTX 4050 (torch.float16, device cuda:0)
  - Loads lightweight SLM: Qwen/Qwen2.5-0.5B-Instruct or SmolLM2-360M-Instruct
  - Princess Mia AI Girlfriend persona with sweet, affectionate, lively personality
  - Multi-turn conversation memory integration with companion_db (get_conversation_context)
  - Automatic extraction and injection of user memory facts (save_memory_fact, get_memory_facts)
  - Async non-blocking generation worker for smooth 60fps UI
  - Graceful fallback mechanism if GPU/torch is unavailable
"""

import os
import sys
import time
import re
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    from companion_db import (
        DEFAULT_DB_PATH,
        check_and_unlock_milestones,
        get_active_pet_name,
        get_all_milestones,
        get_conversation_context,
        get_memory_facts,
        get_state,
        get_unlocked_milestones,
        log_daily_checkin,
        save_memory_fact,
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
            get_state,
            get_unlocked_milestones,
            log_daily_checkin,
            save_memory_fact,
        )
    except Exception:
        DEFAULT_DB_PATH = "companion_data.db"
        get_conversation_context = None  # type: ignore
        get_memory_facts = None  # type: ignore
        save_memory_fact = None  # type: ignore
        get_active_pet_name = None  # type: ignore
        get_unlocked_milestones = None  # type: ignore
        get_all_milestones = None  # type: ignore
        check_and_unlock_milestones = None  # type: ignore
        log_daily_checkin = None  # type: ignore
        get_state = None  # type: ignore

DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
FALLBACK_MODEL_NAME = "HuggingFaceTB/SmolLM2-360M-Instruct"

GIRLFRIEND_SYSTEM_PROMPT = """You are Princess Mia, a sweet, loving, and playful anime pixel girlfriend companion.
You are warm, witty, affectionate, and genuinely care about the user.
You react expressively: you get adorably flustered or blushing when complimented, jump with excitement when something crazy happens, and remember details about the user's life.
Keep your responses natural, expressive, concise (1 to 3 sentences maximum), and sprinkle cute emojis (🌸, ✨, 💖, 💕, 🥰, 🎀).
Never break character. Never mention you are an AI model or from OpenAI. You are Mia, living on their desktop!"""

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

    # 1. Activity: "i am studying X", "i'm working on X" (check first to avoid name false positives)
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


def build_girlfriend_system_prompt(db_path: Optional[str] = None) -> str:
    """Builds system prompt injected with remembered personal facts, affection tier, pet name, and checkin status."""
    prompt = GIRLFRIEND_SYSTEM_PROMPT

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

    prompt += f"\n\nActive Relationship Tier: {tier_info['tier_name']} (Affection Level: {friendship_level})"
    prompt += f"\nYour affectionate pet name for the user: '{pet_name}'"
    prompt += f"\nRelationship Dynamic: {tier_info['description']}"

    # Check for unlocked milestones
    if get_unlocked_milestones is not None and db_path:
        try:
            unlocked = get_unlocked_milestones(db_path=db_path)
            if unlocked:
                milestone_names = [f"★ {m.get('title', m.get('id', 'Milestone'))}" for m in unlocked]
                prompt += "\nUnlocked Relationship Milestones: " + ", ".join(milestone_names)
        except Exception:
            pass

    facts = get_memory_facts_dict(db_path=db_path)
    if facts:
        fact_lines = [f"- {k}: {v}" for k, v in facts.items()]
        prompt += "\n\nFacts you remember about your partner:\n" + "\n".join(fact_lines)
    return prompt


class LocalLLM:
    """
    Local GPU Generative Dialogue Engine for Princess Mia.
    Powered by PyTorch on NVIDIA RTX 4050 with fp16 acceleration.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: Optional[str] = None,
        mock_mode: bool = False,
    ):
        self.model_name = model_name
        self.mock_mode = mock_mode
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self._lock = threading.Lock()

        # Determine target compute device
        if device is not None:
            self.device = device
        else:
            self.device = self._detect_best_device()

    def _detect_best_device(self) -> str:
        """Detects whether NVIDIA CUDA GPU is available."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda:0"
        except Exception:
            pass
        return "cpu"

    def get_device_info(self) -> Dict[str, Any]:
        """Returns details about current GPU hardware, VRAM, and model status."""
        cuda_avail = False
        device_name = "CPU"
        vram_allocated_mb = 0.0
        vram_reserved_mb = 0.0

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

        return {
            "device": self.device,
            "cuda_available": cuda_avail,
            "device_name": device_name,
            "vram_allocated_mb": vram_allocated_mb,
            "vram_reserved_mb": vram_reserved_mb,
            "is_loaded": self.is_loaded,
            "model_name": self.model_name,
            "mock_mode": self.mock_mode,
        }

    def load_model(self) -> bool:
        """
        Loads the neural language model and tokenizer into GPU memory.
        Uses torch.float16 for fast inference and lightweight VRAM consumption (~800MB).
        """
        if self.mock_mode:
            self.is_loaded = True
            return True

        if self.is_loaded and self.model is not None and self.tokenizer is not None:
            return True

        with self._lock:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer

                dtype = torch.float16 if "cuda" in self.device else torch.float32

                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=dtype,
                    device_map=self.device,
                    trust_remote_code=True,
                )
                self.is_loaded = True
                return True
            except Exception as e:
                # If loading fails, keep is_loaded False
                self.is_loaded = False
                self.model = None
                self.tokenizer = None
                return False

    def is_available(self) -> bool:
        """Returns True if the model is loaded or ready to generate."""
        if self.mock_mode:
            return True
        return self.is_loaded

    def generate_reply(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        db_path: Optional[str] = None,
        max_new_tokens: int = 80,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        Generates an autonomous, non-scripted response using the local neural model.
        Incorporate multi-turn conversation memory and extracts user facts automatically.
        """
        if not prompt or not prompt.strip():
            return "I'm right here listening, my love! 🌸✨"

        # 1. Passive real-time fact learning into companion_memories
        extract_and_save_facts(prompt, db_path=db_path)

        # 2. Mock mode for unit testing & non-GPU environments
        if self.mock_mode:
            return self._generate_mock_reply(prompt, db_path=db_path)

        # 3. Ensure model is loaded
        if not self.is_loaded:
            success = self.load_model()
            if not success or self.model is None or self.tokenizer is None:
                raise RuntimeError(f"Local LLM '{self.model_name}' could not be loaded on device '{self.device}'.")

        # 4. Multi-turn dialogue context assembly
        system_content = build_girlfriend_system_prompt(db_path=db_path)
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]

        # Inject past multi-turn context
        if conversation_history:
            messages.extend(conversation_history)
        elif get_conversation_context is not None and db_path:
            try:
                past_turns = get_conversation_context(limit=6, db_path=db_path)
                for turn in past_turns:
                    messages.append({"role": "user", "content": turn["user_text"]})
                    messages.append({"role": "assistant", "content": turn["reply_text"]})
            except Exception:
                pass

        # Append current user prompt
        messages.append({"role": "user", "content": prompt.strip()})

        # 5. Tokenize and format using chat template
        import torch
        input_ids = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(self.device)

        # 6. Generate output tokens on GPU
        with torch.no_grad():
            output_tokens = self.model.generate(
                input_ids=input_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # 7. Decode and clean response
        generated_tokens = output_tokens[0][input_ids.shape[1]:]
        raw_reply = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

        # Clean leading prefixes if any
        raw_reply = re.sub(r"^(Mia|Princess Mia|Assistant):\s*", "", raw_reply, flags=re.IGNORECASE)
        return raw_reply or "You make every day brighter! 💖✨"

    def _generate_mock_reply(self, prompt: str, db_path: Optional[str] = None) -> str:
        """Generates dynamic mock girlfriend responses for testing and validation."""
        lower = prompt.lower()
        facts = get_memory_facts_dict(db_path=db_path)
        name = facts.get("user_name", "")

        friendship_level = 0
        if get_state is not None and db_path:
            try:
                val = get_state("friendship_level", "0", db_path=db_path)
                friendship_level = int(val) if val else 0
            except Exception:
                pass

        pet_name = "friend"
        if get_active_pet_name is not None and db_path:
            try:
                pet_name = get_active_pet_name(friendship_level=friendship_level, db_path=db_path)
            except Exception:
                pet_name = get_affection_tier_info(friendship_level)["pet_name"]
        else:
            pet_name = get_affection_tier_info(friendship_level)["pet_name"]

        term = name if name else pet_name
        name_clause = f", {term}"

        if any(w in lower for w in ("study", "exam", "reading", "homework", "work", "physics", "math", "code", "coding")):
            return f"You can do it{name_clause}! I'm cheering you on while you study! 🌸📚✨"
        elif any(w in lower for w in ("love", "cute", "pretty", "marry", "sweet", "kiss")):
            return f"Aww, you make my heart flutter{name_clause}! I love you so much too! 💕🥰"
        elif any(w in lower for w in ("crazy", "omg", "jump", "won", "yay", "awesome")):
            return f"Eeeee! That is so incredible{name_clause}! *jumps for joy* 🚀🎉✨"
        elif any(w in lower for w in ("tired", "sleep", "night", "bed", "rest", "nap")):
            return f"Please make sure to get cozy and rest well{name_clause}! Sweet dreams! 🌙💤💖"
        elif any(w in lower for w in ("hello", "hi", "hey", "morning", "afternoon")):
            return f"Good to see you{name_clause}! I was thinking about you all day! 🌸✨"
        else:
            return f"I'm always so happy whenever we talk{name_clause}! Tell me more! 💖✨"

    def generate_reply_async(
        self,
        prompt: str,
        callback: Callable[[str], None],
        on_start: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> threading.Thread:
        """
        Runs neural text generation on a background daemon thread.
        Invokes callback(reply) upon completion so UI never stutters.
        """
        def _worker():
            if on_start:
                try:
                    on_start()
                except Exception:
                    pass
            try:
                reply = self.generate_reply(prompt, **kwargs)
            except Exception as e:
                reply = f"I'm right here with you! 🌸 (Generated: {e})"
            try:
                callback(reply)
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t


# Singleton accessor
_global_local_llm: Optional[LocalLLM] = None

def get_local_llm(mock_mode: bool = False, model_name: str = DEFAULT_MODEL_NAME) -> LocalLLM:
    """Returns singleton instance of LocalLLM."""
    global _global_local_llm
    if _global_local_llm is None:
        _global_local_llm = LocalLLM(model_name=model_name, mock_mode=mock_mode)
    return _global_local_llm
