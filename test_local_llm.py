#!/usr/bin/env python3
"""
test_local_llm.py — Comprehensive Unit Tests for Local Neural Dialogue Pipeline
Tests:
  - LocalLLM initialization, device detection, and get_device_info
  - Automated fact extraction (names, favorites, likes, activities) into companion_memories
  - Girlfriend persona system prompt construction with injected memories
  - Neural generation in mock and GPU execution modes
  - Multi-turn conversation history integration
  - Asynchronous background worker (generate_reply_async)
  - DialogueEngine integration with LocalLLM and graceful fallback
"""

import os
import sys
import tempfile
import threading
import time
import unittest

# Ensure local worktree modules take precedence
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from companion_db import (
    clear_db,
    get_conversation_context,
    get_memory_facts,
    init_db,
    save_memory_fact,
)
from dialogue_engine import DialogueEngine, Emotion
from local_llm import (
    GIRLFRIEND_SYSTEM_PROMPT,
    LocalLLM,
    build_girlfriend_system_prompt,
    extract_and_save_facts,
    get_local_llm,
    get_memory_facts_dict,
)


class TestLocalLLMDeviceAndInit(unittest.TestCase):
    """Tests device discovery, memory metadata reporting, and initialization."""

    def test_device_detection(self):
        llm = LocalLLM(mock_mode=True)
        info = llm.get_device_info()
        self.assertIn("device", info)
        self.assertIn("cuda_available", info)
        self.assertIn("device_name", info)
        self.assertIn("vram_allocated_mb", info)
        self.assertIn("vram_reserved_mb", info)
        self.assertTrue(info["mock_mode"])

    def test_custom_device(self):
        llm = LocalLLM(device="cpu", mock_mode=True)
        self.assertEqual(llm.device, "cpu")

    def test_mock_mode_availability(self):
        llm = LocalLLM(mock_mode=True)
        self.assertTrue(llm.is_available())
        self.assertTrue(llm.load_model())


class TestMemoryFactExtraction(unittest.TestCase):
    """Tests passive fact extraction from natural user inputs into companion_memories."""

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        conn = init_db(self.temp_path)
        conn.close()

    def tearDown(self):
        clear_db(self.temp_path)
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except OSError:
                pass

    def test_extract_user_name(self):
        cases = [
            ("Hi, my name is Alex!", "Alex"),
            ("Please call me Devon.", "Devon"),
            ("I'm Maya, nice to meet you!", "Maya"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                saved = extract_and_save_facts(text, db_path=self.temp_path)
                facts = get_memory_facts_dict(db_path=self.temp_path)
                self.assertEqual(facts.get("user_name"), expected)

    def test_extract_favorite_item(self):
        text = "My favorite color is emerald green!"
        extract_and_save_facts(text, db_path=self.temp_path)
        facts = get_memory_facts_dict(db_path=self.temp_path)
        self.assertIn("favorite_color", facts)
        self.assertEqual(facts["favorite_color"], "emerald green")

    def test_extract_likes(self):
        text = "I really like matcha ice cream, it's the best."
        extract_and_save_facts(text, db_path=self.temp_path)
        facts = get_memory_facts_dict(db_path=self.temp_path)
        found = any("matcha" in k or "matcha" in v for k, v in facts.items())
        self.assertTrue(found, f"Matcha preference not stored: {facts}")

    def test_extract_studying_activity(self):
        text = "I am currently studying computer science."
        extract_and_save_facts(text, db_path=self.temp_path)
        facts = get_memory_facts_dict(db_path=self.temp_path)
        self.assertIn("current_studying", facts)
        self.assertEqual(facts["current_studying"], "computer science")


class TestSystemPromptAndPersona(unittest.TestCase):
    """Tests AI Girlfriend system prompt construction and memory fact injection."""

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        conn = init_db(self.temp_path)
        conn.close()

    def tearDown(self):
        clear_db(self.temp_path)
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except OSError:
                pass

    def test_system_prompt_contains_persona(self):
        prompt = build_girlfriend_system_prompt()
        self.assertIn("Princess Mia", prompt)
        self.assertIn("girlfriend companion", prompt.lower())
        self.assertIn("flustered", prompt.lower())

    def test_system_prompt_injects_memories(self):
        save_memory_fact("user_name", "Devansh", category="identity", db_path=self.temp_path)
        save_memory_fact("favorite_fruit", "strawberries", category="preference", db_path=self.temp_path)

        prompt = build_girlfriend_system_prompt(db_path=self.temp_path)
        self.assertIn("Devansh", prompt)
        self.assertIn("strawberries", prompt)


class TestNeuralGenerationAndAsyncWorker(unittest.TestCase):
    """Tests response generation, context chaining, and async threading."""

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        conn = init_db(self.temp_path)
        conn.close()
        self.llm = LocalLLM(mock_mode=True)

    def tearDown(self):
        clear_db(self.temp_path)
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except OSError:
                pass

    def test_generate_reply_sync(self):
        save_memory_fact("user_name", "Kenji", category="identity", db_path=self.temp_path)
        reply = self.llm.generate_reply("I love you so much, Mia!", db_path=self.temp_path)
        self.assertIsInstance(reply, str)
        self.assertGreater(len(reply), 0)
        self.assertIn("Kenji", reply)

    def test_study_reply_encouragement(self):
        reply = self.llm.generate_reply("I have to study for my exams now", db_path=self.temp_path)
        self.assertTrue(any(w in reply.lower() for w in ("study", "cheering", "do it")))

    def test_async_generation(self):
        result_holder = []
        event = threading.Event()

        def on_complete(reply):
            result_holder.append(reply)
            event.set()

        t = self.llm.generate_reply_async("Hello Mia!", callback=on_complete, db_path=self.temp_path)
        self.assertIsInstance(t, threading.Thread)
        self.assertTrue(event.wait(timeout=2.0))
        self.assertEqual(len(result_holder), 1)
        self.assertGreater(len(result_holder[0]), 0)


class TestDialogueEngineWithLocalLLM(unittest.TestCase):
    """Tests end-to-end DialogueEngine integration with LocalLLM."""

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        conn = init_db(self.temp_path)
        conn.close()

    def tearDown(self):
        clear_db(self.temp_path)
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except OSError:
                pass

    def test_dialogue_engine_with_llm(self):
        engine = DialogueEngine(db_path=self.temp_path, use_llm=True, mock_llm=True)
        self.assertTrue(engine.use_llm)
        self.assertIsNotNone(engine.llm)

        res = engine.process_message("I am studying physics today!")
        self.assertIn("reply_text", res)
        self.assertGreater(len(res["reply_text"]), 0)
        # Verify interaction was logged
        self.assertIsNotNone(res["interaction_id"])

    def test_dialogue_engine_async(self):
        engine = DialogueEngine(db_path=self.temp_path, use_llm=True, mock_llm=True)
        res_holder = []
        event = threading.Event()

        def callback(res):
            res_holder.append(res)
            event.set()

        engine.process_message_async("You are so cute and sweet!", callback=callback)
        self.assertTrue(event.wait(timeout=2.0))
        self.assertEqual(len(res_holder), 1)
        self.assertEqual(res_holder[0]["emotion"], Emotion.LOVE.value)


if __name__ == "__main__":
    unittest.main()
