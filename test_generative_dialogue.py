#!/usr/bin/env python3
"""
test_generative_dialogue.py — Comprehensive Unit Tests for Open-Domain Generative Engine

Validates:
  1. The 15 mandatory open-domain conversational scenarios
  2. Multi-turn context memory and past learning recall
  3. Handling of unknown/unfamiliar words (graceful inquiry, no crash)
  4. Conversational course-correction and simplification (ELI5)
  5. Separation of auxiliary ML perception from LLM intelligence
  6. Token-aware sliding context window truncation
  7. Token streaming and asynchronous background generation
  8. Device metadata and hardware telemetry (RTX 4050 GPU VRAM)
  9. Graceful fallback handling when LLM is offline
"""

import os
import sys
import tempfile
import threading
import time
import unittest
from typing import List

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from companion_db import (
    clear_db,
    get_conversation_context,
    get_relevant_memories,
    init_db,
    log_interaction,
    save_memory_fact,
    truncate_conversation_tokens,
)
from dialogue_engine import DialogueEngine, Emotion
from local_llm import (
    DEFAULT_MODEL_NAME,
    LocalLLM,
    STATUS_READY,
    STATUS_UNAVAILABLE,
    build_girlfriend_system_prompt,
    get_affection_tier_info,
    get_memory_facts_dict,
)


class TestMandatoryConversationScenarios(unittest.TestCase):
    """
    Validates that the companion generates contextually rich, unique responses
    across all 15 required open-domain scenarios rather than falling back to
    canned/generic templates like 'I'm listening! Tell me more!'.
    """

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        conn = init_db(self.temp_path)
        conn.close()
        self.engine = DialogueEngine(db_path=self.temp_path, use_llm=True, mock_llm=True)

    def tearDown(self):
        clear_db(self.temp_path)
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except OSError:
                pass

    def test_all_15_scenarios_produce_contextual_non_generic_replies(self):
        scenarios = [
            ("What is quantum entanglement?", ["quantum", "particles", "entanglement", "distance"]),
            ("Explain Kubernetes like I'm a beginner.", ["kubernetes", "container", "manager", "ship"]),
            ("Have you heard of sonder?", ["sonder", "stranger", "complex", "vivid"]),
            ("What do you think about black holes?", ["black hole", "gravity", "singularity", "event horizon"]),
            ("I had a terrible day today.", ["rough day", "beside you", "relax", "sorry"]),
            ("Can you explain how a CPU cache works?", ["cpu", "cache", "sram", "fast"]),
            ("Let's talk about something interesting.", ["octopus", "hearts", "blood", "interesting"]),
            ("Do you think time travel is possible?", ["time travel", "relativity", "future", "einstein"]),
            ("What is the difference between TCP and UDP?", ["tcp", "udp", "reliability", "packet"]),
            ("Tell me something I probably don't know.", ["shark", "trees", "older", "years"]),
            ("Let's change the topic.", ["switch", "topic", "mind", "explore"]),
            ("What did I tell you I was learning earlier?", ["learning", "studies", "earlier"]),
            ("What does this unusual word mean: zqorvex?", ["zqorvex", "vocabulary", "dictionary", "mean"]),
            ("Actually, explain that in simpler words.", ["simple", "blocks", "piece", "work"]),
            ("Haha, that's not what I meant.", ["oops", "misunderstanding", "mind", "ears"]),
        ]

        generic_templates = {
            "I'm listening! Tell me more! 🌸",
            "Always happy to chat with you! ✨",
            "I'm right here beside you! 💖",
        }

        generated_responses = []

        for prompt, expected_keywords in scenarios:
            with self.subTest(prompt=prompt):
                res = self.engine.process_message(prompt)
                reply = res["reply_text"]
                self.assertNotIn(reply, generic_templates, f"Generic template returned for: {prompt}")
                self.assertEqual(res["source"], "llm")
                
                # Verify keyword relevance
                reply_lower = reply.lower()
                matched = any(kw.lower() in reply_lower for kw in expected_keywords)
                self.assertTrue(
                    matched,
                    f"Response '{reply}' for prompt '{prompt}' did not contain any expected keywords: {expected_keywords}"
                )
                generated_responses.append(reply)

        # Ensure all 15 scenarios produced distinctly unique answers
        self.assertEqual(len(set(generated_responses)), 15, "Repetitive replies detected across distinct topics!")

    def test_multi_turn_past_learning_recall(self):
        """Validates that the companion accurately recalls learning topics across conversation turns."""
        # 1. User introduces learning topic
        self.engine.process_message("I am learning Go and building a Redis-compatible key-value store!")
        facts = get_memory_facts_dict(db_path=self.temp_path)
        self.assertTrue(any("go" in str(v).lower() for v in facts.values()))

        # 2. User asks what they were learning earlier
        res = self.engine.process_message("What did I tell you I was learning earlier?")
        self.assertIn("Go", res["reply_text"])
        self.assertIn("learning", res["reply_text"].lower())

    def test_unknown_words_handled_gracefully(self):
        """Unfamiliar vocabulary (slang, sci-fi terms) should prompt clarification rather than generic templates."""
        res = self.engine.process_message("Do you understand what zqorvex is?")
        self.assertIn("zqorvex", res["reply_text"].lower())
        self.assertTrue(any(w in res["reply_text"].lower() for w in ("vocabulary", "dictionary", "invented", "mean")))

    def test_conversational_correction(self):
        """Validates adaptive course-correction when the user clarifies intent."""
        res = self.engine.process_message("Haha, that's not what I meant at all!")
        self.assertTrue(any(w in res["reply_text"].lower() for w in ("oops", "misunderstanding", "mind", "ears")))


class TestTokenAwareContextTruncation(unittest.TestCase):
    """Tests token budgeting, sliding window, and SQLite conversation memory."""

    def test_truncate_conversation_tokens(self):
        long_messages = [
            {"role": "user", "content": "A" * 700},      # ~200 tokens
            {"role": "assistant", "content": "B" * 700}, # ~200 tokens
            {"role": "user", "content": "C" * 700},      # ~200 tokens
            {"role": "assistant", "content": "D" * 700}, # ~200 tokens
            {"role": "user", "content": "Recent question"},
            {"role": "assistant", "content": "Recent answer"},
        ]
        # Request context budget of max 250 tokens
        trimmed = truncate_conversation_tokens(long_messages, max_tokens=250)
        self.assertLess(len(trimmed), len(long_messages))
        # Most recent turn must be preserved
        self.assertEqual(trimmed[-2]["content"], "Recent question")
        self.assertEqual(trimmed[-1]["content"], "Recent answer")

    def test_get_conversation_context_with_token_budget(self):
        temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_fd)
        try:
            init_db(temp_path)
            for i in range(15):
                log_interaction(f"user query {i}", f"companion reply {i}", emotion="NORMAL", db_path=temp_path)

            context = get_conversation_context(limit=10, max_tokens=500, db_path=temp_path)
            self.assertGreater(len(context), 0)
            self.assertLessEqual(len(context), 20)
            # Must remain chronological
            self.assertEqual(context[-1]["role"], "assistant")
        finally:
            clear_db(temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_relevant_memories_retrieval(self):
        temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_fd)
        try:
            init_db(temp_path)
            save_memory_fact("favorite_language", "Python", category="preference", db_path=temp_path)
            save_memory_fact("current_studying", "Quantum Computing", category="activity", db_path=temp_path)
            save_memory_fact("user_name", "Alex", category="identity", db_path=temp_path)

            # Query relevant to quantum
            rel = get_relevant_memories("Can you help with my quantum physics homework?", db_path=temp_path)
            self.assertGreater(len(rel), 0)
            self.assertEqual(rel[0]["key"], "current_studying")
            self.assertIn("Quantum", rel[0]["value"])
        finally:
            clear_db(temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestAuxiliaryMLSeparation(unittest.TestCase):
    """
    Tests that the ML emotion/intent classifier acts strictly as auxiliary perception
    (providing signals, expressions, aura) and DOES NOT gate or override LLM intelligence.
    """

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        conn = init_db(self.temp_path)
        conn.close()
        self.engine = DialogueEngine(db_path=self.temp_path, use_llm=True, mock_llm=True)

    def tearDown(self):
        clear_db(self.temp_path)
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except OSError:
                pass

    def test_neutral_normal_classification_still_generates_intelligent_answer(self):
        """Even if classifier labels input NORMAL and QUESTION/CHAT, LLM generates full answer."""
        res = self.engine.process_message("Can you explain how a CPU cache works?")
        self.assertEqual(res["emotion"], Emotion.NORMAL.value)
        self.assertIn(res["intent"], ("QUESTION", "CHAT"))
        self.assertEqual(res["source"], "llm")
        self.assertIn("cpu cache", res["reply_text"].lower())
        self.assertNotIn("Tell me more", res["reply_text"])

    def test_auxiliary_signals_present_alongside_generated_text(self):
        res = self.engine.process_message("You are so sweet and I love spending time with you!")
        self.assertEqual(res["emotion"], Emotion.LOVE.value)
        self.assertGreater(res["emotion_confidence"], 0.5)
        self.assertEqual(res["source"], "llm")
        self.assertIn("suggested_sound", res)
        self.assertIn("affection_tier", res)
        self.assertIn("pet_name", res)


class TestStreamingAndAsyncGeneration(unittest.TestCase):
    """Tests token streaming generator and asynchronous background worker."""

    def test_stream_generator_yields_tokens(self):
        llm = LocalLLM(mock_mode=True)
        tokens = []
        gen = llm.generate_reply_stream("Tell me about sonder.")
        for tok in gen:
            tokens.append(tok)
        self.assertGreater(len(tokens), 1)
        full_text = "".join(tokens)
        self.assertIn("sonder", full_text.lower())

    def test_process_message_async_with_tokens(self):
        engine = DialogueEngine(use_llm=True, mock_llm=True)
        streamed_tokens = []
        result_holder = []
        event = threading.Event()

        def on_token(tok):
            streamed_tokens.append(tok)

        def on_done(res):
            result_holder.append(res)
            event.set()

        engine.process_message_async(
            "What is quantum entanglement?",
            callback=on_done,
            on_token=on_token,
            persist=False,
        )

        self.assertTrue(event.wait(timeout=3.0))
        self.assertEqual(len(result_holder), 1)
        self.assertGreater(len(streamed_tokens), 0)
        self.assertIn("quantum", result_holder[0]["reply_text"].lower())


class TestDeviceMetadataAndOfflineFallback(unittest.TestCase):
    """Tests hardware detection, VRAM reporting, and offline fallback handling."""

    def test_hardware_device_reporting(self):
        llm = LocalLLM(mock_mode=True)
        info = llm.get_device_info()
        self.assertIn("device", info)
        self.assertIn("cuda_available", info)
        self.assertIn("device_name", info)
        self.assertIn("vram_total_mb", info)
        self.assertIn("status", info)

    def test_fallback_marked_when_llm_fails(self):
        # Configure non-existent host to simulate offline/failure with mock_mode=False
        failing_llm = LocalLLM(host="http://127.0.0.1:99999", mock_mode=False)
        failing_llm.is_loaded = False
        failing_llm.status = STATUS_UNAVAILABLE

        engine = DialogueEngine(use_llm=True, llm=failing_llm)
        res = engine.process_message("Good morning Mia!", persist=False)
        self.assertIn("reply_text", res)
        # Should gracefully fall back to contextual template and clearly record source
        self.assertEqual(res["source"], "fallback")


if __name__ == "__main__":
    unittest.main()
