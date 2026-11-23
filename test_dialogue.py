#!/usr/bin/env python3
"""
test_dialogue.py — Comprehensive Unit Tests for dialogue_engine.py
Tests:
  - Emotion classification (HAPPY, PLAYFUL, SHY, LOVE, NORMAL)
  - Smart greeting detection
  - Time-of-day categorization and greetings
  - Contextual responses (identity, well-being, stats, farewells)
  - Integration with companion_db.py (friendship progression, interaction logging, greeting count)
  - Stateless execution mode (db_path=None / persist=False)
"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime

from dialogue_engine import (
    Emotion,
    DialogueEngine,
    classify_emotion,
    get_time_based_greeting,
    get_time_of_day,
    is_greeting,
    respond,
)
from companion_db import clear_db, get_recent_interactions, get_stats


class TestEmotionClassification(unittest.TestCase):
    """Tests emotion classification rules and precedence."""

    def test_emotion_love(self):
        inputs = [
            "I love you so much!",
            "You are so cute and adorable",
            "Such a pretty sweetheart ♥",
            "Sending you lots of love and hugs 💕",
            "You look gorgeous today",
        ]
        for text in inputs:
            with self.subTest(text=text):
                self.assertEqual(classify_emotion(text), Emotion.LOVE.value)

    def test_emotion_shy(self):
        inputs = [
            "I'm feeling a bit shy today...",
            "*blushes* I don't know what to say",
            "Sorry, feeling nervous and timid",
            "Uwu don't look at me like that",
            "I'm so flustered right now",
        ]
        for text in inputs:
            with self.subTest(text=text):
                self.assertEqual(classify_emotion(text), Emotion.SHY.value)

    def test_emotion_playful(self):
        inputs = [
            "Tell me a funny joke haha!",
            "Let's play a game together lol",
            "You are so silly hehe",
            "Time to dance and spin around!",
            "Wink wink, catch me if you can ;)",
        ]
        for text in inputs:
            with self.subTest(text=text):
                self.assertEqual(classify_emotion(text), Emotion.PLAYFUL.value)

    def test_emotion_happy(self):
        inputs = [
            "I am so happy today!",
            "We won the match, awesome news!",
            "This is fantastic and wonderful!",
            "Yay! Feeling glad and cheerful! 🎉",
            "Such a great day ahead! 😊",
        ]
        for text in inputs:
            with self.subTest(text=text):
                self.assertEqual(classify_emotion(text), Emotion.HAPPY.value)

    def test_emotion_normal_and_neutral(self):
        inputs = [
            "What time is it right now?",
            "Can you tell me about the solar system?",
            "The quick brown fox jumps over the lazy dog.",
            "I have some work to finish.",
            "",
            "   ",
        ]
        for text in inputs:
            with self.subTest(text=text):
                self.assertEqual(classify_emotion(text), Emotion.NORMAL.value)


class TestGreetingDetection(unittest.TestCase):
    """Tests detection of greeting intent in user messages."""

    def test_recognized_greetings(self):
        positive_samples = [
            "hello!",
            "Hi Mia",
            "HEY THERE!",
            "howdy partner",
            "Good morning everyone",
            "good afternoon",
            "Good evening Mia",
            "yo!",
            "sup?",
            "what's up?",
            "Greetings to you!",
            "hiya friend",
        ]
        for phrase in positive_samples:
            with self.subTest(phrase=phrase):
                self.assertTrue(is_greeting(phrase), f"Failed to recognize greeting: {phrase}")

    def test_non_greetings(self):
        negative_samples = [
            "Tell me about philosophy",
            "What is the weather outside?",
            "I need help with this bug",
            "Cats are very independent animals",
            "",
            "   ",
        ]
        for phrase in negative_samples:
            with self.subTest(phrase=phrase):
                self.assertFalse(is_greeting(phrase), f"False positive greeting: {phrase}")


class TestTimeOfDayGreetings(unittest.TestCase):
    """Tests time-of-day classification and standard greeting phrases."""

    def test_time_of_day_slots(self):
        morning_dt = datetime(2026, 11, 23, 8, 30)
        afternoon_dt = datetime(2026, 11, 23, 14, 15)
        evening_dt = datetime(2026, 11, 23, 19, 45)
        night_late_dt = datetime(2026, 11, 23, 23, 10)
        night_early_dt = datetime(2026, 11, 23, 2, 0)

        self.assertEqual(get_time_of_day(morning_dt), "morning")
        self.assertEqual(get_time_of_day(afternoon_dt), "afternoon")
        self.assertEqual(get_time_of_day(evening_dt), "evening")
        self.assertEqual(get_time_of_day(night_late_dt), "night")
        self.assertEqual(get_time_of_day(night_early_dt), "night")

    def test_time_based_greetings(self):
        morning_dt = datetime(2026, 11, 23, 9, 0)
        afternoon_dt = datetime(2026, 11, 23, 13, 0)
        evening_dt = datetime(2026, 11, 23, 18, 0)
        night_dt = datetime(2026, 11, 23, 23, 30)

        self.assertIn("morning", get_time_based_greeting(morning_dt).lower())
        self.assertIn("afternoon", get_time_based_greeting(afternoon_dt).lower())
        self.assertIn("evening", get_time_based_greeting(evening_dt).lower())
        self.assertIn("evening", get_time_based_greeting(night_dt).lower())


class TestDialogueEngineContextAndDB(unittest.TestCase):
    """Tests contextual reply logic and SQLite companion_db integration."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        self.engine = DialogueEngine(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_greeting_increments_greeting_count_and_friendship(self):
        """A greeting should increment both greeting count and friendship level."""
        morning_dt = datetime(2026, 11, 23, 9, 0)
        res = self.engine.process_message("Good morning Mia!", dt=morning_dt)

        self.assertTrue(res["is_greeting"])
        self.assertEqual(res["time_of_day"], "morning")
        self.assertIn("Good morning", res["reply_text"])
        self.assertEqual(res["greeting_count"], 1)
        self.assertGreaterEqual(res["friendship_level"], 1)
        self.assertIsNotNone(res["interaction_id"])

        # Check database records
        stats = get_stats(self.db_path)
        self.assertEqual(stats["total_interactions"], 1)
        self.assertEqual(stats["greeting_count"], 1)
        self.assertEqual(stats["last_interaction"]["emotion"], res["emotion"])

    def test_non_greeting_only_increments_friendship(self):
        """A regular message should increase friendship but not greeting count."""
        res = self.engine.process_message("Tell me a funny joke haha!")
        self.assertFalse(res["is_greeting"])
        self.assertEqual(res["emotion"], Emotion.PLAYFUL.value)
        self.assertEqual(res["greeting_count"], 0)
        self.assertGreaterEqual(res["friendship_level"], 1)

        stats = get_stats(self.db_path)
        self.assertEqual(stats["greeting_count"], 0)
        self.assertEqual(stats["total_interactions"], 1)

    def test_love_emotion_gives_bonus_friendship(self):
        """LOVE emotion gives +2 friendship points."""
        res = self.engine.process_message("You are so cute and adorable! ♥")
        self.assertEqual(res["emotion"], Emotion.LOVE.value)
        self.assertEqual(res["friendship_level"], 2)

    def test_identity_inquiry(self):
        """Questions about Mia's identity return companion self-introduction."""
        res = self.engine.process_message("Who are you?")
        self.assertIn("Mia", res["reply_text"])
        self.assertIn("companion", res["reply_text"].lower())

    def test_wellbeing_inquiry(self):
        """Asking how Mia is doing returns cheerful status."""
        res = self.engine.process_message("How are you doing today?")
        self.assertIn("wonderful", res["reply_text"].lower())

    def test_friendship_stats_inquiry(self):
        """Asking about friendship or stats returns level and greeting counts."""
        # Seed some interactions
        self.engine.process_message("Hello!", dt=datetime(2026, 11, 23, 10, 0))
        res = self.engine.process_message("What is our friendship level?")
        self.assertIn("friendship level", res["reply_text"].lower())
        self.assertIn("greetings", res["reply_text"].lower())

    def test_farewell_and_good_night(self):
        """Farewell messages trigger sweet send-offs."""
        res_night = self.engine.process_message("Good night, going to sleep!")
        self.assertIn("dreams", res_night["reply_text"].lower())

        res_bye = self.engine.process_message("Goodbye for now!")
        self.assertIn("soon", res_bye["reply_text"].lower())

    def test_stateless_execution(self):
        """Engine executes cleanly without database (db_path=None or persist=False)."""
        stateless_engine = DialogueEngine(db_path=None)
        res = stateless_engine.process_message("Hi Mia, you are awesome!")
        self.assertEqual(res["emotion"], Emotion.HAPPY.value)
        self.assertTrue(res["is_greeting"])
        self.assertIsNone(res["interaction_id"])
        self.assertEqual(res["friendship_level"], 0)

    def test_module_convenience_respond(self):
        """respond() module function executes end-to-end with temp db."""
        res = respond("Hello world!", db_path=self.db_path)
        self.assertTrue(res["is_greeting"])
        self.assertIsNotNone(res["reply_text"])


if __name__ == "__main__":
    unittest.main()
