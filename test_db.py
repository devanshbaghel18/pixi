#!/usr/bin/env python3
"""
test_db.py — Comprehensive Unit Tests for companion_db.py
Tests database initialization, schema integrity, interaction logging,
friendship and greeting metrics, and summary statistics.
"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from companion_db import (
    DEFAULT_DB_PATH,
    clear_db,
    get_recent_interactions,
    get_state,
    get_stats,
    increment_friendship,
    increment_greeting,
    init_db,
    log_interaction,
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
        """Verifies schema creation and initial companion_state seeding."""
        conn = init_db(self.db_path)
        
        # Verify tables exist
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        self.assertIn("interactions", tables)
        self.assertIn("companion_state", tables)

        # Verify initial default state values
        friendship = get_state("friendship_level", db_path=self.db_path)
        greetings = get_state("greeting_count", db_path=self.db_path)
        self.assertEqual(friendship, "0")
        self.assertEqual(greetings, "0")

    def test_init_db_idempotency(self):
        """Calling init_db multiple times does not overwrite modified state."""
        init_db(self.db_path)
        increment_friendship(10, db_path=self.db_path)
        
        # Call init_db again
        init_db(self.db_path)
        self.assertEqual(get_state("friendship_level", db_path=self.db_path), "10")

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


if __name__ == "__main__":
    unittest.main()
