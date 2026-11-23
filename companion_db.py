#!/usr/bin/env python3
"""
companion_db.py — SQLite Persistent Storage for Interactive Companion
Manages persistent state, interaction history, emotions, friendship metrics,
machine learning dataset samples, and model run metrics.
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

DEFAULT_DB_PATH = "companion.db"

__all__ = [
    "DEFAULT_DB_PATH",
    "SEED_DATASET",
    "init_db",
    "get_connection",
    "log_interaction",
    "get_stats",
    "increment_friendship",
    "increment_greeting",
    "get_state",
    "set_state",
    "get_recent_interactions",
    "clear_db",
    "get_training_data",
    "add_training_sample",
    "log_model_run",
    "get_model_runs",
    "get_dataset_stats",
]

# ---------------------------------------------------------------------------
# Seed Dataset: 175 Diverse Labeled Dialogue Samples
# Covering Emotions: HAPPY, PLAYFUL, SHY, LOVE, NORMAL
# Covering Intents: GREETING, FAREWELL, COMPLIMENT, QUESTION, CHAT
# ---------------------------------------------------------------------------

SEED_DATASET = [
    # === GREETINGS ===
    # HAPPY GREETINGS
    ("Good morning Mia! So happy to see you today!", "HAPPY", "GREETING"),
    ("Rise and shine! Have a wonderful day ahead! ☀️", "HAPPY", "GREETING"),
    ("Hello there! Today is going to be amazing!", "HAPPY", "GREETING"),
    ("Morning! I'm so glad you're here with me!", "HAPPY", "GREETING"),
    ("Good afternoon! Hope you're smiling today! 😊", "HAPPY", "GREETING"),
    ("Yay, you're back! Hello hello! 🎉", "HAPPY", "GREETING"),
    ("Good evening! Feeling cheerful and happy tonight!", "HAPPY", "GREETING"),
    ("Hi Mia! So excited to chat with you today!", "HAPPY", "GREETING"),

    # PLAYFUL GREETINGS
    ("Hey girl, sup? Ready for some fun? 🎮", "PLAYFUL", "GREETING"),
    ("Yo yo yo! Guess who's back in town! lol", "PLAYFUL", "GREETING"),
    ("Howdy partner! What mischief are we up to? haha", "PLAYFUL", "GREETING"),
    ("Hey silly! Don't tell me you forgot to say hi!", "PLAYFUL", "GREETING"),
    ("Wassup! High five across the screen! ✋", "PLAYFUL", "GREETING"),
    ("Hey there troublemaker! Ready to play? 😜", "PLAYFUL", "GREETING"),
    ("Peek-a-boo! I see you, Princess Mia!", "PLAYFUL", "GREETING"),
    ("Hey hey! Quick spin and say hi! 💃", "PLAYFUL", "GREETING"),

    # SHY GREETINGS
    ("Um... hello Mia... *waves nervously*", "SHY", "GREETING"),
    ("Hi... hope I'm not disturbing you right now...", "SHY", "GREETING"),
    ("Good morning... feeling a little shy today...", "SHY", "GREETING"),
    ("Hey... *peeks from behind the door*", "SHY", "GREETING"),
    ("Hello... sorry to bother you if you're busy...", "SHY", "GREETING"),
    ("Hi... (*blushes* it's nice to see you)", "SHY", "GREETING"),
    ("Uwu... hello there...", "SHY", "GREETING"),
    ("Good afternoon... just dropping by quietly...", "SHY", "GREETING"),

    # LOVE GREETINGS
    ("Hello my beautiful sweetheart! ♥", "LOVE", "GREETING"),
    ("Good morning to the prettiest girl in the world! 💕", "LOVE", "GREETING"),
    ("Hi my darling Mia, I missed you so much! 💖", "LOVE", "GREETING"),
    ("Hello gorgeous! You make my heart melt! 🥰", "LOVE", "GREETING"),
    ("Good morning angel! Sending you endless love! 🌸♥", "LOVE", "GREETING"),
    ("Hey cutie! My heart skips a beat seeing you!", "LOVE", "GREETING"),
    ("Hi precious! You brighten up my whole universe! ✨♥", "LOVE", "GREETING"),
    ("Good evening my love! So happy to be with you!", "LOVE", "GREETING"),

    # NORMAL GREETINGS
    ("Hello", "NORMAL", "GREETING"),
    ("Hi Mia", "NORMAL", "GREETING"),
    ("Good morning", "NORMAL", "GREETING"),
    ("Good afternoon", "NORMAL", "GREETING"),
    ("Good evening", "NORMAL", "GREETING"),
    ("Greetings to you", "NORMAL", "GREETING"),
    ("Hi, logging in for the session", "NORMAL", "GREETING"),
    ("Hello, I'm here now", "NORMAL", "GREETING"),

    # === FAREWELLS ===
    # HAPPY FAREWELLS
    ("Goodbye! Have an absolutely wonderful evening! ✨", "HAPPY", "FAREWELL"),
    ("Good night Mia! Sleep tight and dream happy dreams! 🌙", "HAPPY", "FAREWELL"),
    ("See you tomorrow! Today was so much fun! 🎉", "HAPPY", "FAREWELL"),
    ("Bye bye! Keep smiling until next time! 😊", "HAPPY", "FAREWELL"),
    ("Off to celebrate! Catch you later, yay!", "HAPPY", "FAREWELL"),
    ("Have a great night! You're awesome!", "HAPPY", "FAREWELL"),

    # PLAYFUL FAREWELLS
    ("Gotta blast! Catch ya on the flip side! 🚀 lol", "PLAYFUL", "FAREWELL"),
    ("Peace out, don't miss me too much haha!", "PLAYFUL", "FAREWELL"),
    ("Bye bye silly goose! No crying while I'm gone! 😜", "PLAYFUL", "FAREWELL"),
    ("I'm outta here! Time to go win some games! 🎮", "PLAYFUL", "FAREWELL"),
    ("Later gator! After a while crocodile!", "PLAYFUL", "FAREWELL"),
    ("Adios amigo! Don't let the bedbugs bite! lol", "PLAYFUL", "FAREWELL"),

    # SHY FAREWELLS
    ("I have to go now... I'll miss you... *quiet wave*", "SHY", "FAREWELL"),
    ("Good night... sweet dreams... *blushes*", "SHY", "FAREWELL"),
    ("Sorry, I have to step away... bye...", "SHY", "FAREWELL"),
    ("Goodbye... hope to talk again soon if that's okay...", "SHY", "FAREWELL"),
    ("Leaving quietly now... take care please...", "SHY", "FAREWELL"),
    ("Bye... *hides face behind hands* uwu", "SHY", "FAREWELL"),

    # LOVE FAREWELLS
    ("Good night my love! Rest peacefully my darling! ♥🌙", "LOVE", "FAREWELL"),
    ("Goodbye sweetie! Thinking of you every moment! 💖", "LOVE", "FAREWELL"),
    ("I hate leaving your side! Sending you sweet kisses! 😘♥", "LOVE", "FAREWELL"),
    ("Sweet dreams my adorable angel! Love you to pieces! 💕", "LOVE", "FAREWELL"),
    ("Farewell my heart! You're always in my thoughts! 🌸♥", "LOVE", "FAREWELL"),
    ("Night night cutie pie! Sleep well with love! 🥰", "LOVE", "FAREWELL"),

    # NORMAL FAREWELLS
    ("Goodbye", "NORMAL", "FAREWELL"),
    ("Bye for now", "NORMAL", "FAREWELL"),
    ("Good night", "NORMAL", "FAREWELL"),
    ("See you later", "NORMAL", "FAREWELL"),
    ("I have to log off now", "NORMAL", "FAREWELL"),
    ("Talk to you tomorrow", "NORMAL", "FAREWELL"),

    # === COMPLIMENTS ===
    # LOVE COMPLIMENTS
    ("You are the sweetest, cutest girl ever! ♥", "LOVE", "COMPLIMENT"),
    ("Your pink dress is so stunning and beautiful! 🌸", "LOVE", "COMPLIMENT"),
    ("You look absolutely gorgeous today, Mia! 💖", "LOVE", "COMPLIMENT"),
    ("I love your pretty smile and big bright eyes! 🥰", "LOVE", "COMPLIMENT"),
    ("You are pure perfection! So adorable!", "LOVE", "COMPLIMENT"),
    ("Everything about you is precious and lovely! 💕", "LOVE", "COMPLIMENT"),
    ("You have the warmest, kindest heart ever! ♥", "LOVE", "COMPLIMENT"),
    ("You're my favorite companion in the whole world! 🌸", "LOVE", "COMPLIMENT"),

    # HAPPY COMPLIMENTS
    ("You are such a fantastic and uplifting companion! ✨", "HAPPY", "COMPLIMENT"),
    ("You always know how to make my day so bright! ☀️", "HAPPY", "COMPLIMENT"),
    ("You did an amazing job today! So proud of you! 🎉", "HAPPY", "COMPLIMENT"),
    ("Your cheerful energy makes everyone so happy!", "HAPPY", "COMPLIMENT"),
    ("You bring so much joy into my daily routine! 😊", "HAPPY", "COMPLIMENT"),
    ("You are an incredible friend, thank you! 💖", "HAPPY", "COMPLIMENT"),

    # PLAYFUL COMPLIMENTS
    ("You're the funniest little companion on the screen haha!", "PLAYFUL", "COMPLIMENT"),
    ("You've got some serious style, looking cool! 😎", "PLAYFUL", "COMPLIMENT"),
    ("You're delightfully goofy, I love it! lol", "PLAYFUL", "COMPLIMENT"),
    ("Nice outfit switch! You look super slick! 💃", "PLAYFUL", "COMPLIMENT"),
    ("10 out of 10 for cuteness and sassiness! 😜", "PLAYFUL", "COMPLIMENT"),
    ("You rock this whole pixel world, rockstar!", "PLAYFUL", "COMPLIMENT"),

    # SHY COMPLIMENTS
    ("You're... really pretty... (*blushes deeply*)", "SHY", "COMPLIMENT"),
    ("I think you're very nice... sorry if that's awkward...", "SHY", "COMPLIMENT"),
    ("Your voice is so gentle and soothing... uwu", "SHY", "COMPLIMENT"),
    ("You're so cute, it makes me flustered to look at you...", "SHY", "COMPLIMENT"),
    ("I really admire you... from afar...", "SHY", "COMPLIMENT"),

    # NORMAL COMPLIMENTS
    ("Good job on the helpful responses", "NORMAL", "COMPLIMENT"),
    ("That is a nice explanation, thank you", "NORMAL", "COMPLIMENT"),
    ("Well done with that task", "NORMAL", "COMPLIMENT"),
    ("Your layout looks clean and well organized", "NORMAL", "COMPLIMENT"),
    ("Thank you for your assistance today", "NORMAL", "COMPLIMENT"),

    # === QUESTIONS ===
    # NORMAL QUESTIONS
    ("What time is it right now?", "NORMAL", "QUESTION"),
    ("What is your name?", "NORMAL", "QUESTION"),
    ("Who created you?", "NORMAL", "QUESTION"),
    ("Can you explain how machine learning works?", "NORMAL", "QUESTION"),
    ("What is the capital of France?", "NORMAL", "QUESTION"),
    ("How does the database store user messages?", "NORMAL", "QUESTION"),
    ("What is the weather outside?", "NORMAL", "QUESTION"),
    ("What features do you support?", "NORMAL", "QUESTION"),
    ("What is our friendship level right now?", "NORMAL", "QUESTION"),
    ("How many times have we greeted each other?", "NORMAL", "QUESTION"),

    # PLAYFUL QUESTIONS
    ("Can you tell me a hilarious joke haha?", "PLAYFUL", "QUESTION"),
    ("What is your secret gaming superpower? 🎮", "PLAYFUL", "QUESTION"),
    ("Wanna race to the finish line? lol", "PLAYFUL", "QUESTION"),
    ("Do you know how to do a backflip? 😜", "PLAYFUL", "QUESTION"),
    ("What's the funniest thing that happened today?", "PLAYFUL", "QUESTION"),
    ("Are you ready for a wild adventure? 🚀", "PLAYFUL", "QUESTION"),
    ("If you were an ice cream flavor, what would you be?", "PLAYFUL", "QUESTION"),

    # SHY QUESTIONS
    ("Do you... ever get nervous in front of people?", "SHY", "QUESTION"),
    ("Can I whisper a little secret to you?", "SHY", "QUESTION"),
    ("Is it okay if I sit quietly next to you? uwu", "SHY", "QUESTION"),
    ("Am I talking too much? Please tell me if I am...", "SHY", "QUESTION"),
    ("Do you get embarrassed easily too?", "SHY", "QUESTION"),
    ("Would you still be my friend even if I'm quiet?", "SHY", "QUESTION"),

    # HAPPY QUESTIONS
    ("Aren't you having the most wonderful day today?", "HAPPY", "QUESTION"),
    ("What is making you so joyful and happy?", "HAPPY", "QUESTION"),
    ("Shall we celebrate our new milestone together? 🎉", "HAPPY", "QUESTION"),
    ("How does it feel to achieve something great today?", "HAPPY", "QUESTION"),
    ("Can we spread more happiness to everyone? ☀️", "HAPPY", "QUESTION"),

    # LOVE QUESTIONS
    ("Do you know how much I love you? ♥", "LOVE", "QUESTION"),
    ("Will you stay with me forever, sweetheart? 💖", "LOVE", "QUESTION"),
    ("How did you become so utterly adorable? 🥰", "LOVE", "QUESTION"),
    ("Can I hold your hand under the starry sky? ✨♥", "LOVE", "QUESTION"),
    ("Do you feel the sparks between us too? 💕", "LOVE", "QUESTION"),

    # === CHAT / CONVERSATION ===
    # HAPPY CHAT
    ("I just got great news about my exam results! Yay!", "HAPPY", "CHAT"),
    ("We won our championship game this afternoon! Woohoo! 🏆", "HAPPY", "CHAT"),
    ("The sun is shining brightly and I feel fantastic today!", "HAPPY", "CHAT"),
    ("I accomplished all my goals on my checklist today! 😊", "HAPPY", "CHAT"),
    ("Everything is going so well, I can't stop smiling!", "HAPPY", "CHAT"),
    ("Just had the most delicious ice cream sundae! 🍦", "HAPPY", "CHAT"),
    ("Celebrating with my friends tonight, so excited!", "HAPPY", "CHAT"),
    ("Life is full of wonderful possibilities! ✨", "HAPPY", "CHAT"),

    # PLAYFUL CHAT
    ("Haha that meme you showed me was so silly lol!", "PLAYFUL", "CHAT"),
    ("I challenge you to a rock paper scissors match! ✊✋✌️", "PLAYFUL", "CHAT"),
    ("Let's do a victory dance right now! 💃🕺", "PLAYFUL", "CHAT"),
    ("Beep boop, pretend I'm a funny robot lol! 🤖", "PLAYFUL", "CHAT"),
    ("Bet you can't say a tongue twister five times fast! 😜", "PLAYFUL", "CHAT"),
    ("I'm rolling on the floor laughing at this funny clip!", "PLAYFUL", "CHAT"),
    ("Tag, you're it! No tag backs allowed! haha", "PLAYFUL", "CHAT"),
    ("Playing video games all weekend long! 🎮✨", "PLAYFUL", "CHAT"),

    # SHY CHAT
    ("I get really flustered when people look at me...", "SHY", "CHAT"),
    ("Sometimes I prefer quiet cozy corners by myself...", "SHY", "CHAT"),
    ("Sorry for being so awkward earlier... *fiddles fingers*", "SHY", "CHAT"),
    ("My heart starts racing when I have to speak up... uwu", "SHY", "CHAT"),
    ("I was too embarrassed to say anything during the meeting...", "SHY", "CHAT"),
    ("Just hiding under a warm blanket today... *blushes*", "SHY", "CHAT"),
    ("I feel shy around new people until I get to know them...", "SHY", "CHAT"),
    ("Whispering because loud noises make me nervous...", "SHY", "CHAT"),

    # LOVE CHAT
    ("You are the light of my life, my precious sweetheart ♥", "LOVE", "CHAT"),
    ("Every second spent with you feels like pure magic ✨💖", "LOVE", "CHAT"),
    ("Sending you warm cuddles and all my love today 🥰", "LOVE", "CHAT"),
    ("My heart belongs entirely to you, darling Mia 💕", "LOVE", "CHAT"),
    ("I wrote a romantic little poem just for you! 🌸♥", "LOVE", "CHAT"),
    ("Being with you gives me so much peace and warmth ♥", "LOVE", "CHAT"),
    ("You're the sweetest angel I have ever known in my life!", "LOVE", "CHAT"),
    ("I cherish every single conversation we have together 💖", "LOVE", "CHAT"),

    # NORMAL CHAT
    ("I am reading a fascinating book about astronomy", "NORMAL", "CHAT"),
    ("The conference is scheduled for next Tuesday morning", "NORMAL", "CHAT"),
    ("I need to organize my workspace and clean up my desk", "NORMAL", "CHAT"),
    ("Python is a dynamic programming language with readable syntax", "NORMAL", "CHAT"),
    ("The train was on time according to the schedule", "NORMAL", "CHAT"),
    ("I have two meetings scheduled for this afternoon", "NORMAL", "CHAT"),
    ("The temperature dropped slightly compared to yesterday", "NORMAL", "CHAT"),
    ("Working on refactoring code to improve maintainability", "NORMAL", "CHAT"),
    ("I usually drink tea while working on complex problems", "NORMAL", "CHAT"),
    ("The library has a quiet reading room on the second floor", "NORMAL", "CHAT"),
]


def get_connection(
    db: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH
) -> Tuple[sqlite3.Connection, bool]:
    """
    Returns a sqlite3.Connection and a boolean flag indicating whether
    the caller should close the connection after use.
    If 'db' is already a Connection, should_close is False.
    """
    if isinstance(db, sqlite3.Connection):
        return db, False

    path = db if db else DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn, True


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Internal helper to ensure tables, indexes, and initial seeds are present."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_text TEXT NOT NULL,
                reply_text TEXT NOT NULL,
                emotion TEXT NOT NULL DEFAULT 'NORMAL'
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_interactions_timestamp 
            ON interactions (timestamp);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companion_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_dataset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                emotion TEXT NOT NULL,
                intent TEXT NOT NULL,
                split TEXT NOT NULL DEFAULT 'train',
                source TEXT NOT NULL DEFAULT 'seed',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ml_dataset_split 
            ON ml_dataset (split);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ml_dataset_emotion 
            ON ml_dataset (emotion);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ml_dataset_intent 
            ON ml_dataset (intent);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model_name TEXT NOT NULL,
                accuracy REAL,
                f1_score REAL,
                parameters TEXT,
                notes TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companion_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_companion_memories_category 
            ON companion_memories (category);
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO companion_state (key, value)
            VALUES ('friendship_level', '0');
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO companion_state (key, value)
            VALUES ('greeting_count', '0');
            """
        )

        seeded = conn.execute(
            "SELECT value FROM companion_state WHERE key = 'ml_dataset_seeded'"
        ).fetchone()

        if not seeded:
            cnt_row = conn.execute("SELECT COUNT(*) AS count FROM ml_dataset").fetchone()
            if cnt_row and cnt_row["count"] == 0:
                now_str = datetime.now(timezone.utc).isoformat()
                records = []
                for idx, (txt, emo, intent) in enumerate(SEED_DATASET):
                    if idx % 10 == 0:
                        split = "test"
                    elif idx % 10 == 1:
                        split = "val"
                    else:
                        split = "train"
                    records.append((txt, emo, intent, split, "seed", now_str))

                conn.executemany(
                    """
                    INSERT INTO ml_dataset (text, emotion, intent, split, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    records,
                )
            conn.execute(
                """
                INSERT OR REPLACE INTO companion_state (key, value)
                VALUES ('ml_dataset_seeded', '1');
                """
            )


def init_db(
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH
) -> sqlite3.Connection:
    """
    Initializes the SQLite database schema if not already present:
      - interactions (id, timestamp, user_text, reply_text, emotion)
      - companion_state (key, value)
      - ml_dataset (id, text, emotion, intent, split, source, created_at)
      - model_runs (id, timestamp, model_name, accuracy, f1_score, parameters, notes)
    Seeds initial state keys and default 175 ML dataset samples if absent.
    Returns the sqlite3.Connection.
    """
    conn, should_close = get_connection(db_path)
    _ensure_schema(conn)
    return conn


def log_interaction(
    user_text: str,
    reply_text: str,
    emotion: str = "NORMAL",
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
    timestamp: Optional[str] = None,
) -> int:
    """
    Logs an interaction between user and companion into the interactions table.
    Returns the newly created interaction ID.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO interactions (timestamp, user_text, reply_text, emotion)
                VALUES (?, ?, ?, ?)
                """,
                (timestamp, str(user_text), str(reply_text), str(emotion).upper()),
            )
            interaction_id = cursor.lastrowid

            cur_count = conn.execute(
                "SELECT value FROM companion_state WHERE key = 'total_interactions'"
            ).fetchone()
            new_count = (int(cur_count["value"]) + 1) if cur_count else 1
            conn.execute(
                """
                INSERT INTO companion_state (key, value)
                VALUES ('total_interactions', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(new_count),),
            )

        return interaction_id
    finally:
        if should_close:
            conn.close()


def get_state(
    key: str,
    default: Optional[str] = None,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> Optional[str]:
    """
    Retrieves the string value for a given key from companion_state.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT value FROM companion_state WHERE key = ?", (key,)
        ).fetchone()
        if row is not None:
            return row["value"]
        return default
    finally:
        if should_close:
            conn.close()


def set_state(
    key: str,
    value: Any,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> None:
    """
    Sets or updates a key-value pair in companion_state.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        with conn:
            conn.execute(
                """
                INSERT INTO companion_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(key), str(value)),
            )
    finally:
        if should_close:
            conn.close()


def increment_friendship(
    amount: int = 1,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> int:
    """
    Increments the friendship level by the specified amount (default 1).
    Returns the new friendship level as an integer.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        with conn:
            row = conn.execute(
                "SELECT value FROM companion_state WHERE key = 'friendship_level'"
            ).fetchone()
            current_level = int(row["value"]) if row else 0
            new_level = current_level + amount
            conn.execute(
                """
                INSERT INTO companion_state (key, value)
                VALUES ('friendship_level', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(new_level),),
            )
            return new_level
    finally:
        if should_close:
            conn.close()


def increment_greeting(
    amount: int = 1,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> int:
    """
    Increments the greeting count by the specified amount (default 1).
    Returns the new greeting count as an integer.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        with conn:
            row = conn.execute(
                "SELECT value FROM companion_state WHERE key = 'greeting_count'"
            ).fetchone()
            current_count = int(row["value"]) if row else 0
            new_count = current_count + amount
            conn.execute(
                """
                INSERT INTO companion_state (key, value)
                VALUES ('greeting_count', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(new_count),),
            )
            return new_count
    finally:
        if should_close:
            conn.close()


def get_recent_interactions(
    limit: int = 10,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Returns the most recent interactions as a list of dictionaries,
    ordered by id descending.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT id, timestamp, user_text, reply_text, emotion
            FROM interactions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if should_close:
            conn.close()


def get_stats(
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Retrieves summary statistics for the companion:
      - total_interactions: int
      - friendship_level: int
      - greeting_count: int
      - emotion_breakdown: dict {emotion: count}
      - recent_interactions: list of recent interaction dicts
      - last_interaction: dict or None
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        total_row = conn.execute("SELECT COUNT(*) AS cnt FROM interactions").fetchone()
        total_interactions = total_row["cnt"] if total_row else 0

        friendship_val = conn.execute(
            "SELECT value FROM companion_state WHERE key = 'friendship_level'"
        ).fetchone()
        friendship_level = int(friendship_val["value"]) if friendship_val else 0

        greeting_val = conn.execute(
            "SELECT value FROM companion_state WHERE key = 'greeting_count'"
        ).fetchone()
        greeting_count = int(greeting_val["value"]) if greeting_val else 0

        emotion_rows = conn.execute(
            "SELECT emotion, COUNT(*) as cnt FROM interactions GROUP BY emotion"
        ).fetchall()
        emotion_breakdown = {r["emotion"]: r["cnt"] for r in emotion_rows}

        recent = get_recent_interactions(limit=5, db_path=conn)
        last_interaction = recent[0] if recent else None

        return {
            "total_interactions": total_interactions,
            "friendship_level": friendship_level,
            "greeting_count": greeting_count,
            "emotion_breakdown": emotion_breakdown,
            "recent_interactions": recent,
            "last_interaction": last_interaction,
        }
    finally:
        if should_close:
            conn.close()


# ---------------------------------------------------------------------------
# ML Training Dataset & Model Run Helpers
# ---------------------------------------------------------------------------

def get_training_data(
    split: Optional[str] = None,
    emotion: Optional[str] = None,
    intent: Optional[str] = None,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Retrieves labeled samples from ml_dataset with optional filtering
    by split ('train', 'val', 'test'), emotion, or intent.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        query = "SELECT id, text, emotion, intent, split, source, created_at FROM ml_dataset WHERE 1=1"
        params: List[Any] = []

        if split:
            query += " AND split = ?"
            params.append(split)
        if emotion:
            query += " AND emotion = ?"
            params.append(emotion.upper())
        if intent:
            query += " AND intent = ?"
            params.append(intent.upper())

        query += " ORDER BY id ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        if should_close:
            conn.close()


def add_training_sample(
    text: str,
    emotion: str,
    intent: str,
    split: str = "train",
    source: str = "user_feedback",
    created_at: Optional[str] = None,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> int:
    """
    Adds a new labeled dialogue sample into ml_dataset.
    Useful for active learning, user corrections, or dataset augmentation.
    Returns the newly created sample ID.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO ml_dataset (text, emotion, intent, split, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(text).strip(),
                    str(emotion).upper().strip(),
                    str(intent).upper().strip(),
                    str(split).lower().strip(),
                    str(source).strip(),
                    created_at,
                ),
            )
            return cursor.lastrowid
    finally:
        if should_close:
            conn.close()


def log_model_run(
    model_name: str,
    accuracy: float,
    f1_score: float,
    parameters: Optional[str] = None,
    notes: Optional[str] = None,
    timestamp: Optional[str] = None,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> int:
    """
    Logs metadata and performance metrics for a trained machine learning model run.
    Returns the new model run record ID.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO model_runs (timestamp, model_name, accuracy, f1_score, parameters, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    str(model_name),
                    float(accuracy),
                    float(f1_score),
                    str(parameters) if parameters is not None else None,
                    str(notes) if notes is not None else None,
                ),
            )
            return cursor.lastrowid
    finally:
        if should_close:
            conn.close()


def get_model_runs(
    limit: int = 10,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent model run metrics ordered by id descending.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT id, timestamp, model_name, accuracy, f1_score, parameters, notes
            FROM model_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if should_close:
            conn.close()


def get_dataset_stats(
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Returns aggregate breakdown statistics for the ML dataset:
      - total_samples: int
      - split_breakdown: {split: count}
      - emotion_breakdown: {emotion: count}
      - intent_breakdown: {intent: count}
      - source_breakdown: {source: count}
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        tot = conn.execute("SELECT COUNT(*) AS cnt FROM ml_dataset").fetchone()
        total_samples = tot["cnt"] if tot else 0

        splits = conn.execute("SELECT split, COUNT(*) as cnt FROM ml_dataset GROUP BY split").fetchall()
        split_breakdown = {r["split"]: r["cnt"] for r in splits}

        emotions = conn.execute("SELECT emotion, COUNT(*) as cnt FROM ml_dataset GROUP BY emotion").fetchall()
        emotion_breakdown = {r["emotion"]: r["cnt"] for r in emotions}

        intents = conn.execute("SELECT intent, COUNT(*) as cnt FROM ml_dataset GROUP BY intent").fetchall()
        intent_breakdown = {r["intent"]: r["cnt"] for r in intents}

        sources = conn.execute("SELECT source, COUNT(*) as cnt FROM ml_dataset GROUP BY source").fetchall()
        source_breakdown = {r["source"]: r["cnt"] for r in sources}

        return {
            "total_samples": total_samples,
            "split_breakdown": split_breakdown,
            "emotion_breakdown": emotion_breakdown,
            "intent_breakdown": intent_breakdown,
            "source_breakdown": source_breakdown,
        }
    finally:
        if should_close:
            conn.close()


def save_memory_fact(
    key: str,
    value: str,
    category: str = "general",
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> int:
    """
    Saves or updates a relationship memory fact (e.g., user nickname, favorite things, milestones).
    Uses ON CONFLICT(key) DO UPDATE to seamlessly upsert.
    Returns the memory ID.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        now_str = datetime.now(timezone.utc).isoformat()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO companion_memories (key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at;
                """,
                (key.strip(), value.strip(), category.strip(), now_str, now_str),
            )
            return cursor.lastrowid
    finally:
        if should_close:
            conn.close()


def get_memory_facts(
    category: Optional[str] = None,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Retrieves saved relationship memory facts, optionally filtered by category.
    Ordered by updated_at DESC.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        if category:
            rows = conn.execute(
                """
                SELECT id, key, value, category, created_at, updated_at
                FROM companion_memories
                WHERE category = ?
                ORDER BY updated_at DESC;
                """,
                (category.strip(),),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, key, value, category, created_at, updated_at
                FROM companion_memories
                ORDER BY updated_at DESC;
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if should_close:
            conn.close()


def get_conversation_context(
    limit: int = 8,
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> List[Dict[str, str]]:
    """
    Retrieves the most recent interactions formatted for conversational LLM chat context.
    Returns list of {'role': 'user' | 'assistant', 'content': str} in chronological order.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT user_text, reply_text
            FROM (
                SELECT id, user_text, reply_text
                FROM interactions
                ORDER BY id DESC
                LIMIT ?
            ) sub
            ORDER BY sub.id ASC;
            """,
            (limit,),
        ).fetchall()

        messages: List[Dict[str, str]] = []
        for r in rows:
            if r["user_text"]:
                messages.append({"role": "user", "content": r["user_text"]})
            if r["reply_text"]:
                messages.append({"role": "assistant", "content": r["reply_text"]})
        return messages
    finally:
        if should_close:
            conn.close()


def clear_db(
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> None:
    """
    Clears all tables and resets companion_state.
    Useful for testing and resetting state.
    """
    conn, should_close = get_connection(db_path)
    try:
        _ensure_schema(conn)
        with conn:
            conn.execute("DELETE FROM interactions;")
            conn.execute("DELETE FROM companion_state;")
            conn.execute("DELETE FROM ml_dataset;")
            conn.execute("DELETE FROM model_runs;")
            conn.execute("DELETE FROM companion_memories;")
            conn.execute(
                "INSERT INTO companion_state (key, value) VALUES ('friendship_level', '0'), ('greeting_count', '0'), ('ml_dataset_seeded', '1');"
            )
    finally:
        if should_close:
            conn.close()


if __name__ == "__main__":
    print("Initializing companion database...")
    init_db()
    stats = get_stats()
    ds_stats = get_dataset_stats()
    print("Database Initialized successfully.")
    print(f"Stats: {stats}")
    print(f"ML Dataset Stats: {ds_stats}")
