#!/usr/bin/env python3
"""
test_db.py — Comprehensive Unit Tests for companion_db.py
Tests database initialization, schema integrity, interaction logging,
friendship and greeting metrics, ML dataset seeding, active learning feedback,
and model run performance metrics.
"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from companion_db import (
    DEFAULT_DB_PATH,
    SEED_DATASET,
    add_training_sample,
    clear_db,
    get_conversation_context,
    get_dataset_stats,
    get_memory_facts,
    get_model_runs,
    get_recent_interactions,
    get_state,
    get_stats,
    get_training_data,
    increment_friendship,
    increment_greeting,
    init_db,
    log_interaction,
    log_model_run,
    save_memory_fact,
    set_state,
)


class TestCompanionDB(unittest.TestCase):
    def setUp(self):
        # Create a unique temporary SQLite file for each test
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_init_db_creates_tables_and_defaults(self):
        """Verifies schema creation, companion_state, and ml_dataset seeding."""
        conn = init_db(self.db_path)
        try:
            # Verify tables exist
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            self.assertIn("interactions", tables)
            self.assertIn("companion_state", tables)
            self.assertIn("ml_dataset", tables)
            self.assertIn("model_runs", tables)
            self.assertIn("companion_memories", tables)

            # Verify initial default state values
            friendship = get_state("friendship_level", db_path=conn)
            greetings = get_state("greeting_count", db_path=conn)
            self.assertEqual(friendship, "0")
            self.assertEqual(greetings, "0")
        finally:
            conn.close()

    def test_init_db_idempotency(self):
        """Calling init_db multiple times does not overwrite modified state or duplicate seed data."""
        conn1 = init_db(self.db_path)
        conn1.close()
        increment_friendship(10, db_path=self.db_path)
        initial_samples = len(get_training_data(db_path=self.db_path))
        
        # Call init_db again
        conn2 = init_db(self.db_path)
        conn2.close()
        self.assertEqual(get_state("friendship_level", db_path=self.db_path), "10")
        self.assertEqual(len(get_training_data(db_path=self.db_path)), initial_samples)

    def test_log_interaction_and_retrieval(self):
        """Tests logging user interactions with text, reply, and emotion."""
        init_db(self.db_path)

        id1 = log_interaction(
            user_text="hello!",
            reply_text="Hi there! It's lovely to see you! ✨",
            emotion="HAPPY",
            db_path=self.db_path,
        )
        self.assertEqual(id1, 1)

        id2 = log_interaction(
            user_text="how are you today?",
            reply_text="I'm feeling wonderful, thank you!",
            emotion="NORMAL",
            db_path=self.db_path,
        )
        self.assertEqual(id2, 2)

        recent = get_recent_interactions(limit=10, db_path=self.db_path)
        self.assertEqual(len(recent), 2)
        # Most recent first
        self.assertEqual(recent[0]["id"], 2)
        self.assertEqual(recent[0]["user_text"], "how are you today?")
        self.assertEqual(recent[0]["emotion"], "NORMAL")
        self.assertEqual(recent[1]["id"], 1)
        self.assertEqual(recent[1]["user_text"], "hello!")
        self.assertEqual(recent[1]["emotion"], "HAPPY")

    def test_custom_timestamp_logging(self):
        """Verifies that an explicit timestamp can be provided."""
        custom_ts = "2026-11-23T10:00:00+00:00"
        log_interaction(
            user_text="test ts",
            reply_text="ok",
            emotion="SHY",
            db_path=self.db_path,
            timestamp=custom_ts,
        )
        recent = get_recent_interactions(limit=1, db_path=self.db_path)
        self.assertEqual(recent[0]["timestamp"], custom_ts)

    def test_increment_friendship(self):
        """Verifies increment_friendship increases level correctly."""
        init_db(self.db_path)
        
        lvl1 = increment_friendship(1, db_path=self.db_path)
        self.assertEqual(lvl1, 1)
        self.assertEqual(get_state("friendship_level", db_path=self.db_path), "1")

        lvl2 = increment_friendship(5, db_path=self.db_path)
        self.assertEqual(lvl2, 6)
        self.assertEqual(get_state("friendship_level", db_path=self.db_path), "6")

    def test_increment_greeting(self):
        """Verifies increment_greeting increases count correctly."""
        init_db(self.db_path)

        count1 = increment_greeting(1, db_path=self.db_path)
        self.assertEqual(count1, 1)

        count2 = increment_greeting(3, db_path=self.db_path)
        self.assertEqual(count2, 4)
        self.assertEqual(get_state("greeting_count", db_path=self.db_path), "4")

    def test_get_stats(self):
        """Verifies full statistical report from database."""
        init_db(self.db_path)
        
        # Empty stats
        empty_stats = get_stats(self.db_path)
        self.assertEqual(empty_stats["total_interactions"], 0)
        self.assertEqual(empty_stats["friendship_level"], 0)
        self.assertEqual(empty_stats["greeting_count"], 0)
        self.assertEqual(empty_stats["emotion_breakdown"], {})
        self.assertIsNone(empty_stats["last_interaction"])

        # Add data
        log_interaction("hi", "hello!", emotion="HAPPY", db_path=self.db_path)
        log_interaction("play game", "yay!", emotion="PLAYFUL", db_path=self.db_path)
        log_interaction("you are sweet", "aww", emotion="LOVE", db_path=self.db_path)
        log_interaction("another one", "sure", emotion="HAPPY", db_path=self.db_path)
        
        increment_friendship(4, db_path=self.db_path)
        increment_greeting(2, db_path=self.db_path)

        stats = get_stats(self.db_path)
        self.assertEqual(stats["total_interactions"], 4)
        self.assertEqual(stats["friendship_level"], 4)
        self.assertEqual(stats["greeting_count"], 2)
        self.assertEqual(
            stats["emotion_breakdown"],
            {"HAPPY": 2, "PLAYFUL": 1, "LOVE": 1},
        )
        self.assertIsNotNone(stats["last_interaction"])
        self.assertEqual(stats["last_interaction"]["user_text"], "another one")
        self.assertEqual(len(stats["recent_interactions"]), 4)

    def test_set_and_get_custom_state(self):
        """Tests general state get/set with fallback defaults."""
        init_db(self.db_path)

        self.assertIsNone(get_state("non_existent_key", db_path=self.db_path))
        self.assertEqual(
            get_state("non_existent_key", default="fallback", db_path=self.db_path),
            "fallback",
        )

        set_state("favorite_color", "pink", db_path=self.db_path)
        self.assertEqual(
            get_state("favorite_color", db_path=self.db_path), "pink"
        )

        # Overwrite state
        set_state("favorite_color", "rose-gold", db_path=self.db_path)
        self.assertEqual(
            get_state("favorite_color", db_path=self.db_path), "rose-gold"
        )

    def test_clear_db(self):
        """Tests clear_db wiping records and resetting defaults."""
        init_db(self.db_path)
        log_interaction("text", "reply", db_path=self.db_path)
        increment_friendship(10, db_path=self.db_path)
        set_state("temp_key", "temp_val", db_path=self.db_path)

        clear_db(self.db_path)

        stats = get_stats(self.db_path)
        self.assertEqual(stats["total_interactions"], 0)
        self.assertEqual(stats["friendship_level"], 0)
        self.assertEqual(stats["greeting_count"], 0)
        self.assertIsNone(get_state("temp_key", db_path=self.db_path))
        self.assertEqual(len(get_training_data(db_path=self.db_path)), 0)

    def test_in_memory_connection(self):
        """Verifies companion_db works with an in-memory SQLite connection."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)

        id1 = log_interaction("test memory", "reply memory", "HAPPY", db_path=conn)
        self.assertEqual(id1, 1)

        lvl = increment_friendship(3, db_path=conn)
        self.assertEqual(lvl, 3)

        stats = get_stats(db_path=conn)
        self.assertEqual(stats["total_interactions"], 1)
        self.assertEqual(stats["friendship_level"], 3)
        conn.close()

    # -----------------------------------------------------------------------
    # ML Dataset & Model Run Tests
    # -----------------------------------------------------------------------

    def test_ml_dataset_seed_count_and_schema(self):
        """Verifies ml_dataset table seeds >= 150 diverse labeled dialogue samples."""
        init_db(self.db_path)
        samples = get_training_data(db_path=self.db_path)
        self.assertGreaterEqual(
            len(samples),
            150,
            f"Expected at least 150 seed samples, got {len(samples)}",
        )

        first = samples[0]
        self.assertIn("id", first)
        self.assertIn("text", first)
        self.assertIn("emotion", first)
        self.assertIn("intent", first)
        self.assertIn("split", first)
        self.assertIn("source", first)
        self.assertEqual(first["source"], "seed")

    def test_ml_dataset_splits_distribution(self):
        """Verifies train, val, and test splits are all populated and non-empty."""
        init_db(self.db_path)
        train_data = get_training_data(split="train", db_path=self.db_path)
        val_data = get_training_data(split="val", db_path=self.db_path)
        test_data = get_training_data(split="test", db_path=self.db_path)

        self.assertGreater(len(train_data), 100)
        self.assertGreater(len(val_data), 10)
        self.assertGreater(len(test_data), 10)
        self.assertEqual(len(train_data) + len(val_data) + len(test_data), len(get_training_data(db_path=self.db_path)))

    def test_ml_dataset_emotion_coverage(self):
        """Verifies all 5 required emotions are represented in the dataset."""
        init_db(self.db_path)
        required_emotions = {"HAPPY", "PLAYFUL", "SHY", "LOVE", "NORMAL"}
        for emo in required_emotions:
            samples = get_training_data(emotion=emo, db_path=self.db_path)
            self.assertGreaterEqual(
                len(samples),
                15,
                f"Emotion '{emo}' has fewer than 15 samples ({len(samples)})",
            )

    def test_ml_dataset_intent_coverage(self):
        """Verifies all 5 required intents are represented in the dataset."""
        init_db(self.db_path)
        required_intents = {"GREETING", "FAREWELL", "COMPLIMENT", "QUESTION", "CHAT"}
        for intent in required_intents:
            samples = get_training_data(intent=intent, db_path=self.db_path)
            self.assertGreaterEqual(
                len(samples),
                15,
                f"Intent '{intent}' has fewer than 15 samples ({len(samples)})",
            )

    def test_add_training_sample(self):
        """Tests adding a new sample via active learning / user feedback."""
        init_db(self.db_path)
        initial_count = len(get_training_data(db_path=self.db_path))

        new_id = add_training_sample(
            text="You did a fantastic job on this module!",
            emotion="HAPPY",
            intent="COMPLIMENT",
            split="train",
            source="user_feedback",
            db_path=self.db_path,
        )
        self.assertGreater(new_id, 0)
        self.assertEqual(len(get_training_data(db_path=self.db_path)), initial_count + 1)

        # Check sample details
        samples = get_training_data(db_path=self.db_path)
        added = next((s for s in samples if s["id"] == new_id), None)
        self.assertIsNotNone(added)
        self.assertEqual(added["text"], "You did a fantastic job on this module!")
        self.assertEqual(added["emotion"], "HAPPY")
        self.assertEqual(added["intent"], "COMPLIMENT")
        self.assertEqual(added["source"], "user_feedback")

    def test_log_model_run_and_retrieval(self):
        """Tests logging model training performance metrics and retrieving them."""
        init_db(self.db_path)

        run_id1 = log_model_run(
            model_name="tfidf_logistic_regression",
            accuracy=0.915,
            f1_score=0.912,
            parameters='{"C": 1.0, "max_iter": 200, "ngram_range": [1, 2]}',
            notes="Initial baseline classifier run",
            db_path=self.db_path,
        )
        self.assertEqual(run_id1, 1)

        run_id2 = log_model_run(
            model_name="tfidf_linear_svc",
            accuracy=0.938,
            f1_score=0.935,
            parameters='{"C": 0.5, "loss": "hinge"}',
            notes="Support vector machine run",
            db_path=self.db_path,
        )
        self.assertEqual(run_id2, 2)

        runs = get_model_runs(limit=5, db_path=self.db_path)
        self.assertEqual(len(runs), 2)
        # Most recent run first
        self.assertEqual(runs[0]["id"], 2)
        self.assertEqual(runs[0]["model_name"], "tfidf_linear_svc")
        self.assertAlmostEqual(runs[0]["accuracy"], 0.938)
        self.assertAlmostEqual(runs[0]["f1_score"], 0.935)
        self.assertIn("hinge", runs[0]["parameters"])

    def test_get_dataset_stats(self):
        """Tests aggregate breakdown metrics for ML dataset."""
        init_db(self.db_path)
        stats = get_dataset_stats(db_path=self.db_path)

        self.assertGreaterEqual(stats["total_samples"], 150)
        self.assertIn("train", stats["split_breakdown"])
        self.assertIn("val", stats["split_breakdown"])
        self.assertIn("test", stats["split_breakdown"])
        self.assertIn("HAPPY", stats["emotion_breakdown"])
        self.assertIn("GREETING", stats["intent_breakdown"])
        self.assertIn("seed", stats["source_breakdown"])

    def test_companion_memories_crud_and_upsert(self):
        """Tests saving, updating, and retrieving relationship memory facts."""
        init_db(self.db_path)

        id1 = save_memory_fact("partner_nickname", "Darling", category="personal", db_path=self.db_path)
        self.assertIsNotNone(id1)
        save_memory_fact("favorite_flower", "Pink Roses", category="preferences", db_path=self.db_path)
        save_memory_fact("anniversary", "November 23", category="milestones", db_path=self.db_path)

        # Retrieve all
        all_memories = get_memory_facts(db_path=self.db_path)
        self.assertEqual(len(all_memories), 3)

        # Retrieve by category
        pref = get_memory_facts(category="preferences", db_path=self.db_path)
        self.assertEqual(len(pref), 1)
        self.assertEqual(pref[0]["key"], "favorite_flower")
        self.assertEqual(pref[0]["value"], "Pink Roses")

        # Test upsert / update on existing key
        save_memory_fact("partner_nickname", "Sweetheart", category="personal", db_path=self.db_path)
        updated = get_memory_facts(category="personal", db_path=self.db_path)
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["value"], "Sweetheart")

    def test_get_conversation_context_format_and_order(self):
        """Tests retrieving conversation context for LLM multi-turn prompting."""
        init_db(self.db_path)

        # Log 4 sequential interactions
        log_interaction("Hello Mia!", "Hello darling! 🌸", emotion="HAPPY", db_path=self.db_path)
        log_interaction("I had a busy day today", "Aww, make sure to take a rest! ✨", emotion="NORMAL", db_path=self.db_path)
        log_interaction("You look so cute!", "Aww, you make my heart flutter! 💖", emotion="LOVE", db_path=self.db_path)
        log_interaction("What are you thinking about?", "I'm thinking about you! 🥰", emotion="LOVE", db_path=self.db_path)

        # Request last 2 interactions context
        context = get_conversation_context(limit=2, db_path=self.db_path)
        # Should contain 4 messages: 2 pairs of user + assistant in chronological order
        self.assertEqual(len(context), 4)
        self.assertEqual(context[0], {"role": "user", "content": "You look so cute!"})
        self.assertEqual(context[1], {"role": "assistant", "content": "Aww, you make my heart flutter! 💖"})
        self.assertEqual(context[2], {"role": "user", "content": "What are you thinking about?"})
        self.assertEqual(context[3], {"role": "assistant", "content": "I'm thinking about you! 🥰"})

    def test_get_conversation_context_empty_and_default_limit(self):
        """Tests get_conversation_context on empty DB and with default limit=8."""
        init_db(self.db_path)
        # Empty DB returns empty list
        self.assertEqual(get_conversation_context(db_path=self.db_path), [])

        # Log 10 interactions
        for i in range(10):
            log_interaction(f"user query {i}", f"companion reply {i}", emotion="NORMAL", db_path=self.db_path)

        # Default limit=8 should return 8 interactions (16 messages) in chronological order
        context = get_conversation_context(db_path=self.db_path)
        self.assertEqual(len(context), 16)
        self.assertEqual(context[0], {"role": "user", "content": "user query 2"})
        self.assertEqual(context[1], {"role": "assistant", "content": "companion reply 2"})
        self.assertEqual(context[-2], {"role": "user", "content": "user query 9"})
        self.assertEqual(context[-1], {"role": "assistant", "content": "companion reply 9"})

    def test_memory_facts_nonexistent_category(self):
        """Tests get_memory_facts returns empty list for nonexistent category."""
        init_db(self.db_path)
        save_memory_fact("name", "Mia", category="identity", db_path=self.db_path)
        self.assertEqual(get_memory_facts(category="nonexistent", db_path=self.db_path), [])


if __name__ == "__main__":
    unittest.main()
