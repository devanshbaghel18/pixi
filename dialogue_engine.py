#!/usr/bin/env python3
"""
dialogue_engine.py — Conversational & Response Logic Engine for Princess Mia Companion

Provides:
  - Emotion classification: HAPPY, PLAYFUL, SHY, LOVE, NORMAL
  - Smart greeting detection
  - Time-of-day contextual greetings (morning, afternoon, evening, night)
  - Interactive response generation based on sentiment, context, and friendship
  - Full persistence integration with companion_db.py
"""

import os
import random
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from companion_db import (
        DEFAULT_DB_PATH,
        get_state,
        get_stats,
        increment_friendship,
        increment_greeting,
        init_db,
        log_interaction,
        set_state,
    )
except ImportError:
    from .companion_db import (
        DEFAULT_DB_PATH,
        get_state,
        get_stats,
        increment_friendship,
        increment_greeting,
        init_db,
        log_interaction,
        set_state,
    )


class Emotion(str, Enum):
    HAPPY = "HAPPY"
    PLAYFUL = "PLAYFUL"
    SHY = "SHY"
    LOVE = "LOVE"
    NORMAL = "NORMAL"


VALID_EMOTIONS = tuple(e.value for e in Emotion)

# Regex patterns for emotions (ordered by specificity and priority)
EMOTION_PATTERNS = {
    Emotion.LOVE: [
        r"\b(love|marry|kiss|cute|adorable|sweetheart|darling|beautiful|pretty|gorgeous|heart|crush|precious|ilu|ily|sweetie|bae)\b",
        r"[♥❤💕💖💗💓💘]",
    ],
    Emotion.SHY: [
        r"\b(shy|blush|embarrass(ed|ing)?|nervous|secret|whisper|flustered|aww+|uwu|sorry|pardon|oops|timid|modest)\b",
        r"(/w\\|\(//w//\)|\*blushes\*|\*hides\*)",
    ],
    Emotion.PLAYFUL: [
        r"\b(play|game|joke|funny|haha+|hehe+|lol|rofl|lmao|silly|dance|spin|wink|tease|prank|tag|giggle|trick)\b",
        r"(;\)|😜|🤪|✨\s*dance)",
    ],
    Emotion.HAPPY: [
        r"\b(happy|yay|great|awesome|wonderful|fantastic|amazing|excited|glad|hooray|smile|smiling|cheerful|delighted|joy|blessed|good|best)\b",
        r"(:\)|😊|😄|😃|🎉|🎊)",
    ],
}

GREETING_PATTERNS = [
    r"\b(hello|hi|hey|heya|hiya|howdy|yo|sup|greetings)\b",
    r"\bgood\s+(morning|afternoon|evening|day|night)\b",
    r"\bwhat('?s|\s+is)\s+up\b",
]

# Time of day response templates
GREETING_RESPONSES = {
    "morning": [
        "Good morning! Wishing you a bright and beautiful day! ☀️",
        "Rise and shine! I'm so glad to see you this morning! 🌸",
        "Morning! Ready for a wonderful day together? ✨",
    ],
    "afternoon": [
        "Good afternoon! I hope your day is going smoothly! 🌸",
        "Hello there! Taking a nice afternoon break? ✨",
        "Good afternoon! Seeing you always brightens my day! 💖",
    ],
    "evening": [
        "Good evening! How has your day been? ✨",
        "Evening! It's so lovely spending time with you tonight! 🌙",
        "Good evening! Time to relax and enjoy the moment! 🌸",
    ],
    "night": [
        "Good evening! Getting late, make sure to get cozy! 🌙",
        "Hello night owl! I'm happy you're here with me! ✨",
        "A peaceful night to you! Remember to rest well soon! 💤",
    ],
}

EMOTION_RESPONSES = {
    Emotion.LOVE: [
        "Aww, you make my heart flutter! 🥰💖",
        "Eeeek! You're making me blush so red! ♥✨",
        "You're the sweetest! I love spending time with you too! 🌸♥",
    ],
    Emotion.SHY: [
        "Aww, don't be shy! We're in this together! 🌸",
        "Hehe, you're making me flustered too... (*^.^*)✨",
        "It's completely okay! I'll always be here cheering for you! 💖",
    ],
    Emotion.PLAYFUL: [
        "Haha, you're so fun! Let's do a little victory spin! 💃✨",
        "Hehe! Playing games with you is the highlight of my day! 🎮🌸",
        "You always know how to make me laugh! 😆🎉",
    ],
    Emotion.HAPPY: [
        "Yay! Your happiness makes me feel so bright and warm! ☀️✨",
        "That's wonderful news! Let's celebrate together! 🎉💖",
        "Woohoo! Sending you the biggest pixel high-five! 🌸🙌",
    ],
    Emotion.NORMAL: [
        "I'm listening! Tell me more! 🌸",
        "Always happy to chat with you! ✨",
        "I'm right here beside you! 💖",
    ],
}


def classify_emotion(text: str) -> str:
    """
    Classifies the emotion of a user message into one of:
      - 'LOVE'
      - 'SHY'
      - 'PLAYFUL'
      - 'HAPPY'
      - 'NORMAL' (default / neutral)
    """
    if not text:
        return Emotion.NORMAL.value

    clean = text.strip().lower()

    # Precedence: LOVE -> SHY -> PLAYFUL -> HAPPY -> NORMAL
    for pat in EMOTION_PATTERNS[Emotion.LOVE]:
        if re.search(pat, clean):
            return Emotion.LOVE.value

    for pat in EMOTION_PATTERNS[Emotion.SHY]:
        if re.search(pat, clean):
            return Emotion.SHY.value

    for pat in EMOTION_PATTERNS[Emotion.PLAYFUL]:
        if re.search(pat, clean):
            return Emotion.PLAYFUL.value

    for pat in EMOTION_PATTERNS[Emotion.HAPPY]:
        if re.search(pat, clean):
            return Emotion.HAPPY.value

    return Emotion.NORMAL.value


def is_greeting(text: str) -> bool:
    """
    Returns True if the text contains a recognized greeting phrase.
    """
    if not text:
        return False
    clean = text.strip().lower()
    return any(re.search(pat, clean) for pat in GREETING_PATTERNS)


def get_time_of_day(dt: Optional[datetime] = None) -> str:
    """
    Categorizes datetime into time-of-day:
      - 'morning'   : 05:00 - 11:59
      - 'afternoon' : 12:00 - 16:59
      - 'evening'   : 17:00 - 21:59
      - 'night'     : 22:00 - 04:59
    """
    if dt is None:
        dt = datetime.now()
    hour = dt.hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 22:
        return "evening"
    else:
        return "night"


def get_time_based_greeting(dt: Optional[datetime] = None) -> str:
    """
    Returns a standard time-based greeting string.
    """
    tod = get_time_of_day(dt)
    if tod == "morning":
        return "Good morning! ☀️"
    elif tod == "afternoon":
        return "Good afternoon! 🌸"
    elif tod == "evening":
        return "Good evening! ✨"
    else:
        return "Good evening! 🌙"


class DialogueEngine:
    """
    Conversational and response logic engine for Princess Mia.
    Integrates greeting detection, emotion classification, time-of-day sensitivity,
    friendship level adaptation, and persistence via companion_db.
    """

    def __init__(self, db_path: Optional[str] = DEFAULT_DB_PATH):
        self.db_path = db_path
        if self.db_path:
            init_db(self.db_path)

    def get_friendship_level(self) -> int:
        """Retrieves the current friendship level from the database."""
        if not self.db_path:
            return 0
        val = get_state("friendship_level", "0", db_path=self.db_path)
        return int(val) if val else 0

    def get_greeting_count(self) -> int:
        """Retrieves the current greeting count from the database."""
        if not self.db_path:
            return 0
        val = get_state("greeting_count", "0", db_path=self.db_path)
        return int(val) if val else 0

    def _select_greeting_response(
        self, user_text: str, dt: Optional[datetime] = None
    ) -> str:
        """Selects greeting response respecting user input and current time of day."""
        clean = user_text.lower()
        tod = get_time_of_day(dt)

        # Check if user specifically greeted with a time of day
        if "good morning" in clean:
            return "Good morning! Wishing you a bright and joyful day! ☀️"
        elif "good afternoon" in clean:
            return "Good afternoon! I hope your day is going wonderfully! 🌸"
        elif "good evening" in clean:
            return "Good evening! Relax and make yourself comfortable! ✨"
        elif "good night" in clean:
            return "Good night! Sweet dreams and rest well! 🌙💤"

        # General greeting, pick according to current time of day
        pool = GREETING_RESPONSES.get(tod, GREETING_RESPONSES["morning"])
        return pool[0]

    def _build_contextual_reply(
        self,
        user_text: str,
        emotion: str,
        is_greet: bool,
        dt: Optional[datetime] = None,
        friendship_level: int = 0,
    ) -> str:
        """Builds a contextual response based on text content, emotion, and friendship."""
        clean = user_text.strip().lower()

        # 1. Greetings
        if is_greet:
            reply = self._select_greeting_response(user_text, dt)
            if friendship_level >= 25:
                reply += " So happy to see my best friend! ♥"
            return reply

        # 2. Stats and Friendship inquiries
        if any(w in clean for w in ("friendship", "stats", "status", "how close")):
            g_count = self.get_greeting_count()
            return (
                f"Our friendship level is {friendship_level}! "
                f"We've shared {g_count} greetings so far! "
                + ("You're truly my best friend! ♥" if friendship_level >= 20 else "Let's keep growing closer! ✨")
            )

        # 3. Companion Identity / Name
        if any(w in clean for w in ("who are you", "what is your name", "what's your name", "your name")):
            return "I'm Mia, your interactive pixel companion! It's so nice to talk with you! 🌸"

        # 4. Well-being
        if any(w in clean for w in ("how are you", "how's it going", "how are things", "how do you feel")):
            return "I'm feeling wonderful, especially now that you're here chatting with me! ✨💖"

        # 5. Night / Sleep / Farewell
        if any(w in clean for w in ("good night", "sleep well", "going to sleep", "going to bed")):
            return "Sweet dreams! Rest well, and I'll be waiting for you tomorrow! 🌙💤"
        if any(w in clean for w in ("bye", "goodbye", "see you", "farewell", "cya")):
            return "See you soon! Don't stay away too long, okay? 👋🌸"

        # 6. Gratitude
        if any(w in clean for w in ("thank you", "thanks", "thx")):
            return "You're so very welcome! Anything for you! 💖"

        # 7. Compliment / Love / Affection
        if emotion == Emotion.LOVE.value:
            pool = EMOTION_RESPONSES[Emotion.LOVE]
            base = pool[0]
            if friendship_level >= 15:
                base += " (I love you so much!) ♥"
            return base

        # 8. Emotion-based fallbacks
        if emotion in EMOTION_RESPONSES:
            pool = EMOTION_RESPONSES[emotion]
            # Deterministic choice based on text hash to be consistent
            idx = abs(hash(clean)) % len(pool)
            return pool[idx]

        return "I'm listening! Tell me more! 🌸"

    def process_message(
        self,
        user_text: str,
        dt: Optional[datetime] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Processes an incoming user message:
          1. Classifies emotion (HAPPY, PLAYFUL, SHY, LOVE, NORMAL)
          2. Detects greeting intent
          3. Evaluates time-of-day
          4. Generates contextual reply
          5. Updates database state and logs interaction (if persist=True and db_path set)

        Returns dictionary with complete interaction details:
          {
            "user_text": str,
            "reply_text": str,
            "emotion": str,
            "is_greeting": bool,
            "time_of_day": str,
            "friendship_level": int,
            "greeting_count": int,
            "interaction_id": Optional[int]
          }
        """
        if dt is None:
            dt = datetime.now()

        emotion = classify_emotion(user_text)
        is_greet = is_greeting(user_text)
        tod = get_time_of_day(dt)

        current_friendship = self.get_friendship_level() if persist and self.db_path else 0
        current_greetings = self.get_greeting_count() if persist and self.db_path else 0

        reply = self._build_contextual_reply(
            user_text=user_text,
            emotion=emotion,
            is_greet=is_greet,
            dt=dt,
            friendship_level=current_friendship,
        )

        interaction_id = None
        new_friendship = current_friendship
        new_greetings = current_greetings

        if persist and self.db_path:
            # Determine friendship gain: +2 for LOVE/HAPPY, +1 for others
            f_gain = 2 if emotion in (Emotion.LOVE.value, Emotion.HAPPY.value) else 1
            new_friendship = increment_friendship(f_gain, db_path=self.db_path)

            if is_greet:
                new_greetings = increment_greeting(1, db_path=self.db_path)

            interaction_id = log_interaction(
                user_text=user_text,
                reply_text=reply,
                emotion=emotion,
                db_path=self.db_path,
            )

        return {
            "user_text": user_text,
            "reply_text": reply,
            "emotion": emotion,
            "is_greeting": is_greet,
            "time_of_day": tod,
            "friendship_level": new_friendship,
            "greeting_count": new_greetings,
            "interaction_id": interaction_id,
        }


def respond(
    user_text: str,
    db_path: Optional[str] = DEFAULT_DB_PATH,
    dt: Optional[datetime] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to process a single message with DialogueEngine.
    """
    engine = DialogueEngine(db_path=db_path)
    return engine.process_message(user_text=user_text, dt=dt, persist=persist)


if __name__ == "__main__":
    print("Dialogue Engine interactive test...")
    engine = DialogueEngine()
    test_queries = [
        "Good morning Mia!",
        "You are so pretty and cute! ♥",
        "Tell me a joke, haha!",
        "I'm feeling a bit shy today...",
        "What is our friendship level?",
    ]
    for q in test_queries:
        res = engine.process_message(q)
        print(f"\nUser: {res['user_text']}")
        print(f"Emotion: {res['emotion']} | Greeting: {res['is_greeting']} | Time: {res['time_of_day']}")
        print(f"Mia: {res['reply_text']}")
        print(f"Friendship: {res['friendship_level']} | Greetings: {res['greeting_count']}")
