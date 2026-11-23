#!/usr/bin/env python3
"""
companion_db.py — SQLite Persistent Storage for Interactive Companion
Manages persistent state, interaction history, emotions, and friendship metrics.
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

DEFAULT_DB_PATH = "companion.db"

__all__ = [
    "DEFAULT_DB_PATH",
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


def init_db(
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH
) -> sqlite3.Connection:
    """
    Initializes the SQLite database schema if not already present:
      - interactions (id, timestamp, user_text, reply_text, emotion)
      - companion_state (key, value)
    Seeds initial state keys (friendship_level='0', greeting_count='0') if absent.
    Returns the sqlite3.Connection.
    """
    conn, should_close = get_connection(db_path)
    try:
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
            # Default initial states
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
        return conn
    finally:
        # If a path was passed and the caller only wanted initialization,
        # we still return conn for in-memory DB or caller convenience.
        # But if it's a file path and caller ignores return value, Python GC handles it.
        pass


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
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
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
            
            # Increment total interactions counter in companion_state if desired
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
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
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
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
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
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
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
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
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
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
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
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
        # Total interactions count
        total_row = conn.execute("SELECT COUNT(*) AS cnt FROM interactions").fetchone()
        total_interactions = total_row["cnt"] if total_row else 0
        
        # State values
        friendship_val = conn.execute(
            "SELECT value FROM companion_state WHERE key = 'friendship_level'"
        ).fetchone()
        friendship_level = int(friendship_val["value"]) if friendship_val else 0
        
        greeting_val = conn.execute(
            "SELECT value FROM companion_state WHERE key = 'greeting_count'"
        ).fetchone()
        greeting_count = int(greeting_val["value"]) if greeting_val else 0
        
        # Emotion breakdown
        emotion_rows = conn.execute(
            "SELECT emotion, COUNT(*) as cnt FROM interactions GROUP BY emotion"
        ).fetchall()
        emotion_breakdown = {r["emotion"]: r["cnt"] for r in emotion_rows}
        
        # Recent interactions
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


def clear_db(
    db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
) -> None:
    """
    Clears all interactions and resets companion_state.
    Useful for testing and resetting state.
    """
    init_db(db_path)
    conn, should_close = get_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM interactions;")
            conn.execute("DELETE FROM companion_state;")
            conn.execute(
                "INSERT INTO companion_state (key, value) VALUES ('friendship_level', '0'), ('greeting_count', '0');"
            )
    finally:
        if should_close:
            conn.close()


if __name__ == "__main__":
    print("Initializing companion database...")
    init_db()
    stats = get_stats()
    print("Database Initialized successfully.")
    print(f"Stats: {stats}")
