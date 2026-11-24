#!/usr/bin/env python3
"""
Pixel Art Animated Companion — Princess Mia
Interactive animated pixel art with live breathing, blinking, reactions,
and an animated speech cloud replying when you say "hello".

Supports:
  - Tkinter Desktop GUI Popup (Default if display available)
  - Interactive Animated ANSI Terminal Mode (--terminal)
"""

import sys
import os
import time
import math
import select
import threading
import textwrap
import random
import re

try:
    from dialogue_engine import (
        DialogueEngine,
        Emotion,
        classify_emotion,
        is_greeting,
        get_time_based_greeting,
        respond,
    )
except ImportError:
    try:
        from .dialogue_engine import (
            DialogueEngine,
            Emotion,
            classify_emotion,
            is_greeting,
            get_time_based_greeting,
            respond,
        )
    except Exception:
        DialogueEngine = None
        Emotion = None
        classify_emotion = None
        is_greeting = None
        get_time_based_greeting = None
        respond = None

try:
    from companion_db import (
        add_training_sample,
        get_scene_setting,
        set_scene_setting,
        log_study_session,
        get_study_sessions,
        get_study_stats,
    )
except ImportError:
    try:
        from .companion_db import (
            add_training_sample,
            get_scene_setting,
            set_scene_setting,
            log_study_session,
            get_study_sessions,
            get_study_stats,
        )
    except Exception:
        add_training_sample = None
        get_scene_setting = None
        set_scene_setting = None
        log_study_session = None
        get_study_sessions = None
        get_study_stats = None

try:
    from sound_synth import SoundType, play_chime as synth_play_chime
except ImportError:
    try:
        from .sound_synth import SoundType, play_chime as synth_play_chime
    except Exception:
        SoundType = None
        synth_play_chime = None


# ---------------------------------------------------------------------------
# ML Companion Helpers: Badges and Confidence Aura Properties
# ---------------------------------------------------------------------------

def format_ml_badge(
    intent: str,
    intent_confidence: float,
    emotion: str,
    emotion_confidence: float
) -> str:
    """
    Formats the real-time ML intent badge and emotion confidence percentage.
    Example: '[GREETING] (98%) • Emotion: HAPPY (94%)'
    """
    int_pct = int(round(max(0.0, min(1.0, float(intent_confidence))) * 100))
    emo_pct = int(round(max(0.0, min(1.0, float(emotion_confidence))) * 100))
    int_name = str(intent).upper() if intent else "CHAT"
    emo_name = str(emotion).upper() if emotion else "NORMAL"
    return f"[{int_name}] ({int_pct}%) • Emotion: {emo_name} ({emo_pct}%)"


def get_aura_properties(confidence: float) -> dict:
    """
    Determines visual confidence aura attributes based on ML confidence score (0.0 - 1.0).
    Returns tier ('high', 'medium', 'low'), primary color, outline glow, title, particles, and radius bonus.
    """
    conf = max(0.0, min(1.0, float(confidence)))
    if conf >= 0.85:
        return {
            "tier": "high",
            "color": "#ffd700",       # Radiant Gold
            "outline": "#fff3b0",     # Pale Gold Glow
            "title": "Radiant Gold ✨",
            "particles": ["✨", "✦", "★", "💖"],
            "radius_bonus": 16,
        }
    elif conf >= 0.70:
        return {
            "tier": "medium",
            "color": "#00f0ff",       # Celestial Cyan
            "outline": "#9bf6ff",     # Soft Cyan Glow
            "title": "Celestial Glow 🌟",
            "particles": ["✧", "✦", "🌸"],
            "radius_bonus": 10,
        }
    else:
        return {
            "tier": "low",
            "color": "#b388ff",       # Soft Lavender
            "outline": "#e7c6ff",     # Pale Lavender Glow
            "title": "Soft Lavender 🔮",
            "particles": ["•", "✧"],
            "radius_bonus": 4,
        }

PALETTE = {
    " ": None,                  # Transparent / background

    # Sparkles & Floating Hearts
    "*": (255, 230, 120),       # Gold sparkle
    "+": (255, 245, 180),       # Light sparkle
    "~": (255, 185, 230),       # Soft pink sparkle
    "v": (255, 100, 175),       # Heart vibrant pink
    "V": (210, 40, 120),        # Heart dark outline

    # Hair (Rich Auburn / Caramel Chestnut)
    "H": (65, 30, 18),          # Hair deep outline / shadow
    "h": (120, 58, 32),         # Hair main base
    "L": (180, 98, 55),         # Hair mid-tone
    "l": (230, 155, 95),        # Hair bright highlight
    "j": (255, 205, 155),       # Hair glossy shine

    # Hair Ribbon / Big Head Bow
    "R": (145, 18, 75),         # Bow deep outline
    "r": (215, 40, 120),        # Bow shadow
    "Q": (255, 95, 165),        # Bow main pink
    "q": (255, 170, 215),       # Bow highlight pink
    "W": (255, 255, 255),       # White lace & highlight

    # Skin & Face
    "O": (195, 120, 90),        # Skin shadow contour
    "o": (240, 170, 140),       # Skin soft shade
    "S": (255, 222, 200),       # Skin main base
    "s": (255, 240, 228),       # Skin bright highlight
    "b": (255, 140, 160),       # Soft blush
    "B": (255, 85, 115),        # Deep rosy blush

    # Eyes & Mouth
    "E": (25, 20, 45),          # Eye lash & pupil
    "e": (45, 115, 210),        # Eye sapphire blue iris
    "i": (120, 205, 255),       # Eye bright cyan highlight
    "m": (230, 70, 95),         # Sweet smiling mouth

    # Pink Princess Dress
    "D": (135, 15, 70),         # Dress dark outline
    "d": (195, 30, 105),        # Dress shadow folds
    "P": (255, 85, 155),        # Dress vibrant rose pink
    "p": (255, 135, 188),       # Dress bright pink body
    "X": (255, 185, 220),       # Dress soft pastel highlight
    "x": (255, 225, 242),       # Dress pale pink glow
    "w": (255, 250, 253),       # Frilly white lace / petticoat

    # Waist Sash / Belt Bow
    "Z": (120, 12, 60),         # Sash deep fold
    "z": (180, 25, 95),         # Sash shadow
    "A": (245, 55, 135),        # Sash main pink
    "a": (255, 130, 185),       # Sash highlight

    # Flowers Bouquet held in hands
    "G": (35, 125, 45),         # Foliage dark green
    "g": (75, 195, 75),         # Foliage bright leaf
    "F": (255, 215, 0),         # Flower golden yellow
    "f": (255, 248, 140),       # Flower light petals
    "C": (255, 75, 80),         # Red mini rose blossom

    # Legs, Socks & Shoes
    "k": (248, 248, 255),       # White frilly socks
    "K": (205, 205, 225),       # Socks shadow fold
    "U": (150, 18, 70),         # Mary Jane shoes ruby pink
    "u": (235, 50, 120),        # Mary Jane shoes bright pink
    "M": (95, 12, 45),          # Shoe sole

    # Ground
    ".": (225, 185, 205),       # Ground shadow

    # Speech Cloud (Terminal)
    "Y": (255, 255, 255),       # Cloud white body
    "y": (210, 225, 245),       # Cloud soft shaded edge
    "T": (255, 40, 120),        # Cloud animated text
}

# ---------------------------------------------------------------------------
# Theme Palettes: Princess Pink (Default), Midnight Violet, Golden Sunset
# ---------------------------------------------------------------------------

PALETTE_PRINCESS_PINK = dict(PALETTE)

PALETTE_MIDNIGHT_VIOLET = dict(PALETTE)
PALETTE_MIDNIGHT_VIOLET.update({
    "*": (128, 255, 219),       # Turquoise sparkle
    "+": (114, 239, 221),       # Cyan light sparkle
    "~": (199, 125, 255),       # Soft violet sparkle
    "v": (157, 78, 221),        # Violet heart
    "V": (90, 24, 154),         # Dark violet outline

    # Hair (Silvery Moonlit Lavender / Ash Violet)
    "H": (34, 34, 59),          # Deep shadow
    "h": (74, 78, 105),         # Main base
    "L": (108, 117, 125),       # Mid tone
    "l": (173, 181, 189),       # Highlight
    "j": (233, 236, 239),       # Glossy platinum shine

    # Head Bow
    "R": (36, 0, 70),           # Deep violet outline
    "r": (60, 9, 108),          # Shadow
    "Q": (90, 24, 154),         # Mystic purple
    "q": (157, 78, 221),        # Bright lilac highlight
    "W": (245, 240, 255),       # White/silver lace

    # Dress
    "D": (20, 0, 45),           # Dark night outline
    "d": (50, 10, 85),          # Shadow folds
    "P": (123, 44, 191),        # Royal purple body
    "p": (157, 78, 221),        # Vibrant violet body
    "X": (199, 125, 255),       # Pastel lavender highlight
    "x": (224, 170, 255),       # Soft glowing lilac
    "w": (240, 235, 255),       # Pale starlight lace

    # Sash
    "Z": (16, 0, 43),           # Sash deep fold
    "z": (60, 9, 108),          # Sash shadow
    "A": (90, 24, 154),         # Sash purple
    "a": (157, 78, 221),        # Sash highlight

    # Flowers Bouquet
    "G": (20, 70, 85),          # Dark teal foliage
    "g": (40, 140, 160),        # Bright cyan foliage
    "F": (160, 230, 255),       # Crystal blue blossom
    "f": (210, 245, 255),       # Pale light petals
    "C": (180, 80, 255),        # Violet mini blossom

    # Shoes & Socks
    "k": (235, 235, 250),       # Pale silver-white socks
    "K": (180, 180, 210),       # Socks shadow
    "U": (60, 9, 108),          # Amethyst dark shoe
    "u": (157, 78, 221),        # Bright violet shoe
    "M": (20, 0, 45),           # Shoe sole
    ".": (160, 140, 190),       # Ground shadow
})

PALETTE_GOLDEN_SUNSET = dict(PALETTE)
PALETTE_GOLDEN_SUNSET.update({
    "*": (255, 209, 102),       # Warm amber sparkle
    "+": (255, 243, 176),       # Sunlight sparkle
    "~": (255, 160, 122),       # Peach sparkle
    "v": (231, 111, 81),        # Sunset heart
    "V": (154, 3, 30),          # Warm maroon outline

    # Hair (Espresso & Golden Honey Caramel)
    "H": (32, 15, 7),           # Deep espresso shadow
    "h": (56, 29, 17),          # Warm chocolate base
    "L": (111, 56, 30),         # Warm cinnamon mid-tone
    "l": (176, 125, 56),        # Golden honey highlight
    "j": (252, 211, 77),        # Golden blonde shine

    # Head Bow
    "R": (120, 0, 0),           # Deep crimson outline
    "r": (193, 18, 31),         # Crimson shadow
    "Q": (247, 127, 0),         # Vibrant tangerine
    "q": (252, 191, 73),        # Warm marigold highlight
    "W": (255, 252, 235),       # Warm ivory lace

    # Dress
    "D": (128, 14, 19),         # Deep wine outline
    "d": (173, 40, 49),         # Coral shadow folds
    "P": (255, 107, 107),       # Sunset coral pink body
    "p": (255, 160, 122),       # Light peach body
    "X": (255, 209, 102),       # Golden amber highlight
    "x": (255, 243, 176),       # Soft sun glow
    "w": (255, 250, 230),       # Warm cream lace

    # Sash
    "Z": (120, 20, 20),         # Sash deep fold
    "z": (190, 50, 40),         # Sash shadow
    "A": (244, 162, 97),        # Sash golden peach
    "a": (255, 190, 11),        # Sash bright gold

    # Flowers Bouquet
    "G": (40, 80, 30),          # Warm moss green
    "g": (90, 160, 60),         # Bright olive leaf
    "F": (255, 180, 0),         # Sunburst yellow
    "f": (255, 230, 120),       # Pale sunflower
    "C": (230, 60, 40),         # Scarlet mini rose

    # Shoes & Socks
    "k": (255, 250, 240),       # Creamy socks
    "K": (220, 210, 195),       # Socks warm shadow
    "U": (107, 15, 26),         # Burgundy shoe
    "u": (217, 4, 41),          # Bright ruby-coral shoe
    "M": (55, 6, 23),           # Shoe sole
    ".": (230, 185, 165),       # Ground shadow
})

THEMES = {
    "Princess Pink": PALETTE_PRINCESS_PINK,
    "Midnight Violet": PALETTE_MIDNIGHT_VIOLET,
    "Golden Sunset": PALETTE_GOLDEN_SUNSET,
}

def get_theme_palette(name="Princess Pink"):
    """Returns the palette dictionary for the specified theme name."""
    return THEMES.get(name, THEMES["Princess Pink"])

# ---------------------------------------------------------------------------
# Interactive Scenes & Background Environments
# ---------------------------------------------------------------------------

SCENES = {
    "Sakura Park": {
        "title": "Sakura Park 🌸",
        "theme": "Princess Pink",
        "bg_color": "#14111d",
        "ground_shadow": "#251c2e",
        "particles": "sakura_petals",
        "desc": "Cherry blossoms fluttering softly in spring breeze",
    },
    "Midnight Stars": {
        "title": "Midnight Stars 🌙",
        "theme": "Midnight Violet",
        "bg_color": "#0a0914",
        "ground_shadow": "#151326",
        "particles": "celestial_meteors",
        "desc": "Cosmic balcony under a canopy of twinkling stars and shooting meteors",
    },
    "Cozy Study": {
        "title": "Cozy Study ☕",
        "theme": "Golden Sunset",
        "bg_color": "#181310",
        "ground_shadow": "#2c1f18",
        "particles": "rain_and_steam",
        "desc": "Warm amber lamp glow, window rain droplets, and steaming tea",
    },
    "Sunset Beach": {
        "title": "Sunset Beach 🌅",
        "theme": "Golden Sunset",
        "bg_color": "#1f1016",
        "ground_shadow": "#381c24",
        "particles": "ocean_waves",
        "desc": "Golden horizon with gentle rolling ocean waves and tropical sea breeze",
    },
    "Rooftop Night": {
        "title": "Rooftop Night 🌃",
        "theme": "Midnight Violet",
        "bg_color": "#0d0f1c",
        "ground_shadow": "#191c33",
        "particles": "city_skyline",
        "desc": "Panoramic rooftop overlooking starry night cityscape with glowing windows",
    },
}

DEFAULT_SCENE = "Sakura Park"
VALID_SCENES = ("Sakura Park", "Midnight Stars", "Cozy Study", "Sunset Beach", "Rooftop Night")

def get_scene_data(name="Sakura Park"):
    return SCENES.get(name, SCENES[DEFAULT_SCENE])

def get_friendship_rank(level: int):
    """Returns (rank_title, badge_icon) for a given friendship level."""
    if level >= 30:
        return "Best Friend Forever", "👑"
    elif level >= 20:
        return "Close Companion", "💖"
    elif level >= 10:
        return "Good Friend", "🌸"
    elif level >= 5:
        return "Friendly Acquaintance", "🌱"
    else:
        return "New Friend", "✨"

BASE_ART = [
    # 0..1: Floating heart & sparkles
    "                  ~*~                   ",
    "       *~        vVVv         ~*        ",
    # 2..5: Big cute hair ribbon & head crown
    "        ~       vQQQv        +          ",
    "      RqQR       vVVv        RQqR       ",
    "     RQQQQr  HHHHHHHHHHHH    rQQQQR     ",
    "     rQQQQQRHhhLLllllLLhhHR RQQQQQr     ",
    # 6..9: Glossy hair & forehead bangs
    "      RqqQR HhLljjjjjjllLhH RqqQr       ",
    "       rQr  HhLljjHHHHjjjlLhH rQr       ",
    "        R   HhLjjHssssssHjjjlLhHR   ~   ",
    "   *         HhLljHssssssssHjllLhH  *   ",
    # 10..13: Eyes, lashes, blushing cheeks
    "        HhLLhHssSssssSssHhLLLhH         ",
    "        HhLLhHssSssssSssHhLLLhH         ",
    "        HhLLhHsSEEESSSSEEESHhLLh        ",
    "        HhLLhHSWEeESSSSEeWSHhLLh        ",
    # 14..17: Eye iris, sweet smile, chin contour
    "   ~    HhLLhHSEiEESSSSEEiESHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
    # 18..20: Neck, white lace collar & tiny neck ribbon
    "              OSsSSsSO                  ",
    "             wWddPPddWw                 ",
    "            wWwPaAAaPwWw     ~          ",
    # 21..24: Bodice of pink dress, puffed sleeves, flower bouquet in hands
    "          dPPPwPaAAaPwPPPd              ",
    "         dPPXPdPaAAaPdPXPPd   *         ",
    "        DPPXXPdzZAAAAZzdPXXPPD          ",
    "        DPPXXSOFffFCCFOOSXXPPD          ",
    # 25..28: Hands, flower bouquet, sash bow
    "        HPXSSgffCCFFffgSSXPH            ",
    "   *     HSsOGGCFffCGGOsSH              ",
    "          HHOdZzAAAAAAzDOHH             ",
    "            dZzAAAAAAzZD                ",
    # 29..32: Flared skirt upper tiers
    "           DPpPzAAAAzPpPD               ",
    "          DPPPpAAAAAApPPPD              ",
    "         DPpPXpPAAAAPpXPpPD             ",
    "        DPpPXxxPpPPxxXPpPD      ~       ",
    # 33..36: Flowing ruffled skirt pleats
    "       DPpPXXxxPpPPxxXXPpPD             ",
    "      DPpPXXxxxxPpPxxxxXXPpPD           ",
    "     DPpPXXxxxxwPpPxxxxXXPpPD           ",
    "    DPpPXXxxxwwDPpPDwwxxxXXPpPD   *     ",
    # 37..39: Frilly white lace hemline of dress
    "   DPpPXXxxwwDDwPpPwDDwwxxXXPpPD        ",
    "   dwwwwwwwwwwDdwwdDwwwwwwwwwwd         ",
    "    DDDDDDDDDDDDDDDDDDDDDDDDDD          ",
    # 40..42: Legs, frilly white ankle socks
    "              OSSSO  OSSSO              ",
    "              OSSSO  OSSSO              ",
    "              OwkwO  OwkwO       ~      ",
    # 43..45: Mary Jane pink shoes & ground shadow
    "             uUKKuO  uUKKuO             ",
    "             uUUUUu  uUUUUu             ",
    "             MMMMMM  MMMMMM             ",
    # 46: Ground sparkles
    "       .   ......  ......  .      *     ",
]

# Facial variation layers (Rows 12..17)
FACE_OPEN = [
    "        HhLLhHsSEEESSSSEEESHhLLh        ",
    "        HhLLhHSWEeESSSSEeWSHhLLh        ",
    "   ~    HhLLhHSEiEESSSSEEiESHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

FACE_HALF_BLINK = [
    "        HhLLhHssEEssSSSSssEEsHhLh       ",
    "        HhLLhHsSEEEsSSSSsEEEsHhLh       ",
    "   ~    HhLLhHssSssssSSssssSHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

FACE_BLINK = [
    "        HhLLhHssssssssssssssHhLLh       ",
    "        HhLLhHsSEEEESSSSEEEEsHhLh       ",
    "   ~    HhLLhHssssssssssssssHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

# Happy smiling eyes and rosy blush when greeting
FACE_HAPPY = [
    "        HhLLhHsSssEESSSSEEssSHhLh       ",
    "        HhLLhHsEEEEsSSSsEEEEsHhLh       ",
    "   ~    HhLLhHsSsssSSSSssssSHhLLh  +    ",
    "        HHhhHObBBBBsSSsBBBBbOHhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSsSmmmmSssSOHHHH         ",
]

# Excited anime star eyes when jumping or crazy excitement
FACE_EXCITED = [
    "        HhLLhHsSEE*ESSSSE*EESHhLh       ",
    "        HhLLhHSE*F*ESSSSE*F*SHhLh       ",
    "   *    HhLLhHSE*EESSSSEE*ESHhLLh  *    ",
    "        HHhhHObBBBBsSSsBBBBbOHhh        ",
    "         HHhHOssSmmmmmmSssOHhHH         ",
    "          HHHHOSsSmmmmmmSsSOHHHH        ",
]

# Flustered deep rosy blush when romantic or shy
FACE_BLUSH = [
    "        HhLLhHssEEssSSSSssEEsHhLh       ",
    "        HhLLhHsSEEEsSSSSsEEEsHhLh       ",
    "   v    HhLLhHssSssssSSssssSHhLLh  v    ",
    "        HHhhHOBBBBBsBBsBBBBBHhhhh       ",
    "         HHhHOBBBBBsBBsBBBBBHhHH        ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

# Peaceful sleeping closed eyes for nap mode
FACE_SLEEPING = [
    "        HhLLhHssssssssssssssHhLLh       ",
    "        HhLLhHsSEEEsSSSSsEEEsHhLh       ",
    "   .    HhLLhHssssssssssssssHhLLh  .    ",
    "        HHhhHObBBBBsSSsBBBBbOHhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

# Blown kiss face with fluttering heart eyes and puckered lips
FACE_KISS = [
    "        HhLLhHsSEEESSSSSssssHhLLh       ",
    "        HhLLhHSWEeESSSSsEEEsHhLLh       ",
    "   v    HhLLhHSEiEESSSSSssssHhLLh  v    ",
    "        HHhhHOBBBBBsBBsBBBBBHhhhh       ",
    "         HHhHOBBBBBsBBsBBBBBHhHH        ",
    "          HHHHOSsSmmmmSsSOHHHH          ",
]

# Hand waving arm poses (Overrides rows 14..26, cols 27..40)
WAVE_ARM_1 = {
    14: (27, "     sSSs  * "),
    15: (27, "    sSSSSO   "),
    16: (27, "   dPPXPd    "),
    17: (27, "  dPPXPd     "),
    18: (27, " dPPPw       "),
    19: (27, "wWddP        "),
    20: (27, "wPaAAa       "),
    21: (27, "dPPPwP       "),
    22: (27, "dPPXPd       "),
    23: (27, "DPPXXP       "),
    24: (27, "DPPXXS       "),
    25: (27, "HPXSSg       "),
    26: (27, "HSsOGG       "),
}

WAVE_ARM_2 = {
    14: (27, "   sSSs   *  "),
    15: (27, "   sSSSSO    "),
    16: (27, "   dPPXPd    "),
    17: (27, "  dPPXPd     "),
    18: (27, " dPPPw       "),
    19: (27, "wWddP        "),
    20: (27, "wPaAAa       "),
    21: (27, "dPPPwP       "),
    22: (27, "dPPXPd       "),
    23: (27, "DPPXXP       "),
    24: (27, "DPPXXS       "),
    25: (27, "HPXSSg       "),
    26: (27, "HSsOGG       "),
}

WAVE_ARM_3 = {
    14: (27, "       sSSs *"),
    15: (27, "      sSSSSO "),
    16: (27, "    dPPXPd   "),
    17: (27, "   dPPXPd    "),
    18: (27, " dPPPw       "),
    19: (27, "wWddP        "),
    20: (27, "wPaAAa       "),
    21: (27, "dPPPwP       "),
    22: (27, "dPPXPd       "),
    23: (27, "DPPXXP       "),
    24: (27, "DPPXXS       "),
    25: (27, "HPXSSg       "),
    26: (27, "HSsOGG       "),
}

# Legs tucked up in mid-air during excitement jump (rows 40..46)
JUMP_LEGS_OVERRIDE = {
    40: "              OwkwO  OwkwO              ",
    41: "             uUKKuO  uUKKuO      ~      ",
    42: "             uUUUUu  uUUUUu             ",
    43: "             MMMMMM  MMMMMM             ",
    44: "                                        ",
    45: "                                        ",
    46: "           ......      ......     *     ",
}

# ---------------------------------------------------------------------------
# Action State Machine & Physics Utilities
# ---------------------------------------------------------------------------

class ActionState:
    IDLE = "IDLE"
    WAVING = "WAVING"
    JUMPING = "JUMPING"
    BLUSHING = "BLUSHING"
    CELEBRATING = "CELEBRATING"
    SLEEPING = "SLEEPING"
    KISSING = "KISSING"
    DANCING = "DANCING"

VALID_ACTIONS = (
    ActionState.IDLE,
    ActionState.WAVING,
    ActionState.JUMPING,
    ActionState.BLUSHING,
    ActionState.CELEBRATING,
    ActionState.SLEEPING,
    ActionState.KISSING,
    ActionState.DANCING,
)

def calculate_jump_physics(progress: float, max_height: float = 42.0):
    """
    Computes physics-based jump trajectory with squash and stretch.
    progress: float from 0.0 to 1.0.
    Returns dict: {y_offset, scale_x, scale_y, phase}
    """
    p = max(0.0, min(1.0, float(progress)))
    if p < 0.15:
        crouch_factor = p / 0.15
        scale_y = 1.0 - (0.18 * crouch_factor)
        scale_x = 1.0 + (0.12 * crouch_factor)
        y_offset = 6.0 * crouch_factor
        phase = "crouch"
    elif p < 0.70:
        air_p = (p - 0.15) / 0.55
        arc = math.sin(air_p * math.pi)
        y_offset = -max_height * arc
        v = math.cos(air_p * math.pi)
        stretch = abs(v) * 0.18
        if v > 0.2:
            phase = "ascent"
        elif abs(v) <= 0.2:
            phase = "apex"
        else:
            phase = "descent"
        scale_y = 1.0 + stretch
        scale_x = 1.0 - (stretch * 0.5)
    elif p < 0.85:
        land_p = (p - 0.70) / 0.15
        impact_factor = math.sin(land_p * math.pi)
        scale_y = 1.0 - (0.22 * impact_factor)
        scale_x = 1.0 + (0.18 * impact_factor)
        y_offset = 4.0 * impact_factor
        phase = "land"
    else:
        rec_p = (p - 0.85) / 0.15
        spring = math.cos(rec_p * math.pi * 0.5)
        scale_y = 1.0 + (0.05 * math.sin(rec_p * math.pi * 2.0) * spring)
        scale_x = 1.0 - (0.04 * math.sin(rec_p * math.pi * 2.0) * spring)
        y_offset = 0.0
        phase = "recovery"

    return {
        "y_offset": y_offset,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "phase": phase,
    }

def calculate_twirl_transform(progress: float, num_spins: float = 2.0):
    """
    Computes 360-degree twirl transformation and orbit angle.
    progress: float from 0.0 to 1.0.
    Returns dict: {angle, cos_angle, sin_angle, scale_x, twirl_phase, skirt_flare}
    """
    p = max(0.0, min(1.0, float(progress)))
    angle = p * 2.0 * math.pi * num_spins
    cos_val = math.cos(angle)
    sin_val = math.sin(angle)
    scale_x = abs(cos_val) * 0.8 + 0.2
    quadrant = int((angle % (2.0 * math.pi)) / (math.pi / 2.0)) % 4
    skirt_flare = abs(sin_val) * 8.0
    return {
        "angle": angle,
        "cos_angle": cos_val,
        "sin_angle": sin_val,
        "scale_x": scale_x,
        "twirl_phase": quadrant,
        "skirt_flare": skirt_flare,
    }

# Sparkle patterns for idle animation (Rows 0, 1, 9, 26, 41, 46)
SPARKLE_FRAMES = [
    {
        0: "                  ~*~                   ",
        1: "       *~        vVVv         ~*        ",
        9: "   *         HhLljHssssssssHjllLhH  *   ",
       26: "   *     HSsOGGCFffCGGOsSH              ",
       41: "              OwkwO  OwkwO       ~      ",
       46: "       .   ......  ......  .      *     ",
    },
    {
        0: "                  *~+                   ",
        1: "       +*        vVVv         *~        ",
        9: "   ~         HhLljHssssssssHjllLhH  +   ",
       26: "   +     HSsOGGCFffCGGOsSH              ",
       41: "              OwkwO  OwkwO       *      ",
       46: "       *   ......  ......  *      .     ",
    },
    {
        0: "                  +*~                   ",
        1: "       ~+        vVVv         +*        ",
        9: "   +         HhLljHssssssssHjllLhH  ~   ",
       26: "   ~     HSsOGGCFffCGGOsSH              ",
       41: "              OwkwO  OwkwO       +      ",
       46: "       ~   ......  ......  .      +     ",
    },
]

def build_frame(face_type="OPEN", sparkle_idx=0, wave_frame=0, jump_legs=False, twirl_phase=0, arm_pose=None):
    """Assembles a 47-row character grid with the given face, body action, and sparkle frame."""
    frame = list(BASE_ART)
    
    # Choose face
    if face_type == "BLINK":
        face_rows = FACE_BLINK
    elif face_type == "HALF":
        face_rows = FACE_HALF_BLINK
    elif face_type == "HAPPY":
        face_rows = FACE_HAPPY
    elif face_type == "EXCITED":
        face_rows = FACE_EXCITED
    elif face_type == "BLUSH":
        face_rows = FACE_BLUSH
    elif face_type == "SLEEPING":
        face_rows = FACE_SLEEPING
    elif face_type == "KISS":
        face_rows = FACE_KISS
    else:
        face_rows = FACE_OPEN
        
    for idx, row in enumerate(face_rows):
        frame[12 + idx] = row

    # Arm pose / Waving arm override
    wave_layers = {1: WAVE_ARM_1, 2: WAVE_ARM_2, 3: WAVE_ARM_3}
    if arm_pose:
        for r_idx, (start_c, seg) in arm_pose.items():
            if 0 <= r_idx < len(frame):
                orig = frame[r_idx]
                frame[r_idx] = orig[:start_c] + seg + orig[start_c + len(seg):]
    elif wave_frame in wave_layers:
        wave_map = wave_layers[wave_frame]
        for r_idx, (start_c, seg) in wave_map.items():
            if 0 <= r_idx < len(frame):
                orig = frame[r_idx]
                frame[r_idx] = orig[:start_c] + seg + orig[start_c + len(seg):]

    # Jump legs override
    if jump_legs:
        for r_idx, replacement in JUMP_LEGS_OVERRIDE.items():
            if 0 <= r_idx < len(frame):
                frame[r_idx] = replacement

    # Apply sparkle frame
    sparkle_map = SPARKLE_FRAMES[sparkle_idx % len(SPARKLE_FRAMES)]
    for row_idx, content in sparkle_map.items():
        frame[row_idx] = content
        
    return frame

def render_ansi_grid(lines, palette=None):
    """Renders pixel art lines using unicode half-blocks and 24-bit ANSI colors."""
    if palette is None:
        palette = PALETTE
    num_rows = len(lines)
    num_cols = len(lines[0])
    output = []
    
    for row_idx in range(0, num_rows, 2):
        top_row = lines[row_idx]
        bot_row = lines[row_idx + 1] if row_idx + 1 < num_rows else " " * num_cols
        
        line_chars = []
        for col_idx in range(num_cols):
            top_char = top_row[col_idx] if col_idx < len(top_row) else " "
            bot_char = bot_row[col_idx] if col_idx < len(bot_row) else " "
            
            top_color = palette.get(top_char)
            bot_color = palette.get(bot_char)
            
            if top_color is None and bot_color is None:
                line_chars.append(" ")
            elif top_color is not None and bot_color is None:
                r, g, b = top_color
                line_chars.append(f"\033[38;2;{r};{g};{b}m▀\033[0m")
            elif top_color is None and bot_color is not None:
                r, g, b = bot_color
                line_chars.append(f"\033[38;2;{r};{g};{b}m▄\033[0m")
            else:
                tr, tg, tb = top_color
                br, bg, bb = bot_color
                line_chars.append(f"\033[38;2;{tr};{tg};{tb}m\033[48;2;{br};{bg};{bb}m▀\033[0m")
        
        output.append("".join(line_chars))
    return "\n".join(output)

# ---------------------------------------------------------------------------
# Terminal Mode Animation
# ---------------------------------------------------------------------------

def run_terminal_app(initial_greeting=False, theme_name="Princess Pink", enable_sound=True):
    """Runs interactive animated companion inside the terminal."""
    print("\033[2J\033[H\033[?25l", end="", flush=True)  # Clear screen, hide cursor
    
    speech_active = initial_greeting
    speech_end_time = time.time() + 5.0 if initial_greeting else 0.0
    speech_text = "H E L L O !"
    
    frame_count = 0
    running = True
    input_buffer = ""
    current_theme = theme_name
    palette = get_theme_palette(current_theme)
    engine = DialogueEngine() if DialogueEngine else None
    
    print("\033[38;2;255;105;180m  ✨ ✿ Princess Mia ✿ ✨ — Terminal Companion\033[0m")
    print("\033[38;2;200;180;220m  Type 'hello', '/theme <pink|violet|sunset>', '/chime', or 'q' to exit\033[0m\n")

    last_ml_info = "ML: [READY]"

    try:
        while running:
            now = time.time()
            frame_count += 1
            
            # Check speech cloud active duration
            if speech_active and now > speech_end_time:
                speech_active = False
                
            # Determine face expression
            if speech_active:
                face = "HAPPY"
            else:
                # Idle blinking cycle: blink every ~3.5 seconds (35 frames at 10fps)
                blink_phase = frame_count % 36
                if blink_phase == 32:
                    face = "HALF"
                elif blink_phase in (33, 34):
                    face = "BLINK"
                elif blink_phase == 35:
                    face = "HALF"
                else:
                    face = "OPEN"
                    
            sparkle_idx = (frame_count // 3) % len(SPARKLE_FRAMES)
            grid = build_frame(face, sparkle_idx)
            
            # If speech cloud is active, render cloud lines above her head
            cloud_lines = []
            if speech_active:
                short_text = speech_text[:28]
                cloud_top = "          ╭────────────────────────╮    "
                cloud_mid = f"       (  ✨   {short_text.center(16)}   ✨ )  "
                cloud_bot = "          ╰───────╮  ──────────────╯    "
                cloud_pt1 = "                  ╰─╮                   "
                cloud_pt2 = "                     o                  "
                cloud_lines = [
                    f"\033[1;38;2;255;182;193m{cloud_top}\033[0m",
                    f"\033[1;38;2;255;255;255m\033[48;2;215;40;120m{cloud_mid}\033[0m",
                    f"\033[1;38;2;255;182;193m{cloud_bot}\033[0m",
                    f"\033[38;2;255;200;220m{cloud_pt1}\033[0m",
                    f"\033[38;2;255;200;220m{cloud_pt2}\033[0m",
                ]
            else:
                cloud_lines = ["\033[K" for _ in range(5)]
                
            # Reposition cursor home (flicker-free redraw)
            sys.stdout.write("\033[3;1H")
            for c_line in cloud_lines:
                sys.stdout.write(f"{c_line}\033[K\n")
                
            rendered_art = render_ansi_grid(grid, palette=palette)
            sys.stdout.write(rendered_art + "\n")
            
            # Interactive prompt line at the bottom
            status_hint = f"\033[38;2;170;140;200m[{current_theme} | {last_ml_info} | Chime: {'ON' if enable_sound else 'OFF'}]\033[0m"
            sys.stdout.write(f"\033[K\n{status_hint} \033[1;38;2;255;105;180mSay something:\033[0m {input_buffer}")
            sys.stdout.flush()
            
            # Non-blocking stdin check
            rlist, _, _ = select.select([sys.stdin], [], [], 0.08)
            if rlist:
                ch = sys.stdin.read(1)
                if ch in ("\n", "\r"):
                    cmd = input_buffer.strip()
                    input_buffer = ""
                    lower_cmd = cmd.lower()
                    if lower_cmd in ("q", "quit", "exit"):
                        running = False
                        break
                    elif lower_cmd.startswith("/theme"):
                        if "violet" in lower_cmd or "purple" in lower_cmd:
                            current_theme = "Midnight Violet"
                        elif "sunset" in lower_cmd or "gold" in lower_cmd:
                            current_theme = "Golden Sunset"
                        else:
                            current_theme = "Princess Pink"
                        palette = get_theme_palette(current_theme)
                        speech_active = True
                        speech_text = f"Theme: {current_theme}"
                        speech_end_time = now + 3.0
                    elif lower_cmd in ("/chime", "/sound", "/bell"):
                        enable_sound = not enable_sound
                        speech_active = True
                        speech_text = f"Chime: {'ON' if enable_sound else 'OFF'}"
                        speech_end_time = now + 3.0
                    elif cmd:
                        if engine:
                            res = engine.process_message(cmd)
                            speech_text = res["reply_text"]
                            ml_emo = res.get("emotion", "NORMAL")
                            ml_conf = res.get("emotion_confidence", 0.85)
                            ml_int = res.get("intent", "CHAT")
                            ml_int_conf = res.get("intent_confidence", 0.85)
                            last_ml_info = format_ml_badge(ml_int, ml_int_conf, ml_emo, ml_conf)
                        else:
                            speech_text = "HELLO THERE! 💖"
                            last_ml_info = "ML: [CHAT] (85%)"
                        speech_active = True
                        speech_end_time = now + 5.0
                        if enable_sound:
                            print("\a", end="", flush=True)
                elif ch in ("\x7f", "\x08"):  # Backspace
                    input_buffer = input_buffer[:-1]
                elif ch == "\x1b":  # Escape
                    running = False
                    break
                elif ch.isprintable():
                    input_buffer += ch
                    
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\033[0m\n")  # Restore cursor
        print("Goodbye! ✨\n")

# ---------------------------------------------------------------------------
# Tkinter GUI Desktop Popup Mode
# ---------------------------------------------------------------------------

class PixelGirlPopup:
    def __init__(self, pixel_size=10, initial_greeting=False, theme="Princess Pink", enable_sound=True, scene=None):
        import tkinter as tk
        self.tk = tk
        
        self.root = tk.Tk()
        self.root.title("✨ ✿ Princess Mia ✿ ✨ (Interactive Companion)")
        self.root.configure(bg="#14111d")
        
        self.pixel_size = pixel_size
        self.num_cols = len(BASE_ART[0])
        self.num_rows = len(BASE_ART)
        
        # Dimensions
        self.cloud_height = 110
        self.canvas_w = (self.num_cols * self.pixel_size) + 40
        self.canvas_h = (self.num_rows * self.pixel_size) + self.cloud_height + 20
        self.girl_y_offset = self.cloud_height + 10
        
        # Theme & Audio
        self.current_theme = theme
        self.current_palette = get_theme_palette(self.current_theme)
        self.sound_enabled = enable_sound
        self.theme_buttons = {}

        # Dialogue Engine & State
        self.dialogue_engine = DialogueEngine() if DialogueEngine else None
        self.friendship_level = self.dialogue_engine.get_friendship_level() if self.dialogue_engine else 0
        self.greeting_count = self.dialogue_engine.get_greeting_count() if self.dialogue_engine else 0

        # Animation State
        self.frame_count = 0
        self.start_time = time.time()
        self.speech_active = initial_greeting
        self.speech_text = "HELLO! ♥"
        self.speech_start_time = time.time() if initial_greeting else 0.0
        self.speech_scale = 1.0 if initial_greeting else 0.0
        self.expression = "HAPPY" if initial_greeting else "NORMAL"
        self.last_girl_shift_y = 0.0

        # Action State Machine (IDLE, WAVING, JUMPING, BLUSHING, CELEBRATING)
        self.action_state = ActionState.IDLE
        self.action_start_time = 0.0
        self.action_duration = 0.0
        self.action_y_shift = 0.0
        self.particles = []
        self.action_particles = self.particles
        self.jump_apex_spawned = False
        self.twirl_particle_timer = 0.0

        # Async Thinking Bubble State
        self.is_thinking = False
        self.thinking_text = "Thinking..."
        self.thinking_start_time = 0.0

        # Scene & Environment State
        if scene and scene in SCENES:
            self.current_scene = scene
        else:
            db_p = self.dialogue_engine.db_path if self.dialogue_engine else None
            if get_scene_setting:
                try:
                    s = get_scene_setting("current_scene", default=DEFAULT_SCENE, db_path=db_p)
                    self.current_scene = s if s in SCENES else DEFAULT_SCENE
                except Exception:
                    self.current_scene = DEFAULT_SCENE
            else:
                self.current_scene = DEFAULT_SCENE

        self.scene_buttons = {}
        self.scene_elements = []
        self.scene_particles = self.scene_elements
        self.shooting_star = None
        self.last_shooting_star_time = 0.0
        self.meteors = []
        self.meteor_timer = 0.0

        # ML Emotion, Intent & Active Learning Feedback State
        self.ml_confidence = 0.85
        self.ml_emotion = self.expression
        self.ml_intent = "GREETING" if initial_greeting else "CHAT"
        self.ml_intent_confidence = 0.95 if initial_greeting else 0.85
        self.ml_method = "ml" if self.dialogue_engine else "heuristic"
        self.last_user_text = "hello" if initial_greeting else ""
        self.feedback_given = False
        self.aura_enabled = True
        self.ml_badge_label = None
        self.thumb_up_btn = None
        self.thumb_down_btn = None
        self.feedback_label = None

        # Study Buddy / Pomodoro Focus Mode State
        self.study_duration_minutes = 25
        self.study_timer_running = False
        self.study_duration_secs = 25 * 60
        self.study_remaining_secs = 25 * 60
        self.study_selected_subject = "General"
        self.study_last_tick_time = time.time()
        self.study_streak_days = 0
        self.study_total_minutes = 0
        self.study_completed_sessions = 0
        self.study_subjects = ["General", "Math", "Coding", "Physics", "Reading"]
        self.study_timer_label = None
        self.study_streak_label = None
        self.btn_study_start = None
        self.btn_study_reset = None
        self.study_subject_var = None

        db_p = self.dialogue_engine.db_path if self.dialogue_engine else None
        if get_study_stats:
            try:
                s_stats = get_study_stats(db_p)
                self.study_streak_days = s_stats.get("current_streak_days", 0)
                self.study_total_minutes = s_stats.get("total_minutes", 0)
                self.study_completed_sessions = s_stats.get("completed_sessions", 0)
            except Exception:
                pass
        
        self.build_ui()
        self.init_grid_cells()
        self.init_scene_elements()
        
        # Start animation loop (~30 fps)
        self.root.after(30, self.update_animation)
        
    def set_theme(self, theme_name):
        """Switches the current outfit/color theme and updates canvas pixels."""
        if theme_name not in THEMES:
            return
        self.current_theme = theme_name
        self.current_palette = get_theme_palette(theme_name)
        
        # Update theme button highlights
        for name, btn in self.theme_buttons.items():
            if name == theme_name:
                btn.config(bg="#d81b60", fg="#ffffff")
            else:
                btn.config(bg="#2c1e38", fg="#c0adc8")
                
        # Force re-render of all cells with new colors
        self.refresh_all_cells()
        self.play_chime("CLICK")

    def set_scene(self, scene_name: str, persist: bool = True) -> bool:
        """Switches the interactive background scene environment."""
        if scene_name not in SCENES:
            return False
        self.current_scene = scene_name
        data = get_scene_data(scene_name)

        # Update canvas and root bg
        if hasattr(self, "canvas") and self.canvas:
            self.canvas.config(bg=data["bg_color"])
        if hasattr(self, "root") and self.root:
            self.root.configure(bg=data["bg_color"])

        # Update button highlights
        for name, btn in self.scene_buttons.items():
            if name == scene_name:
                btn.config(bg="#d81b60", fg="#ffffff")
            else:
                btn.config(bg="#2c1e38", fg="#c0adc8")

        # Synchronize theme if scene defines an outfit theme
        target_theme = data.get("theme")
        if target_theme and target_theme in THEMES:
            self.set_theme(target_theme)

        # Persist scene preference to DB
        if persist and set_scene_setting:
            db_p = self.dialogue_engine.db_path if self.dialogue_engine else None
            try:
                set_scene_setting("current_scene", scene_name, db_path=db_p)
            except Exception:
                pass

        # Re-initialize ambient elements for new scene
        self.init_scene_elements()
        self.play_chime("CLICK")
        return True

    def init_scene_elements(self):
        """Initializes ambient elements appropriate for the active scene."""
        self.scene_elements = []
        self.shooting_star = None
        self.meteors = []
        self.meteor_timer = 0.0
        w = self.canvas_w
        h = self.canvas_h

        if self.current_scene == "Sakura Park":
            for _ in range(22):
                self.scene_elements.append({
                    "type": "petal",
                    "x": random.uniform(0, w),
                    "y": random.uniform(0, h),
                    "vx": random.uniform(0.6, 1.8),
                    "vy": random.uniform(0.8, 2.2),
                    "size": random.uniform(3.0, 6.0),
                    "phase": random.uniform(0, 2 * math.pi),
                    "rot_speed": random.uniform(1.5, 3.5),
                    "char": random.choice(["🌸", "❀", "·", "✿"]),
                    "color": random.choice(["#ffb7b2", "#ffccd5", "#ffc6ff", "#ffa6c9", "#ffd1dc"]),
                })
        elif self.current_scene == "Midnight Stars":
            for _ in range(35):
                self.scene_elements.append({
                    "type": "star",
                    "x": random.uniform(8, w - 8),
                    "y": random.uniform(8, h - 30),
                    "size": random.uniform(1.2, 3.0),
                    "twinkle_speed": random.uniform(1.5, 4.5),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["✦", "✧", "⋆", "•", "★"]),
                    "color": random.choice(["#ffffff", "#e0e7ff", "#c7d2fe", "#fef08a", "#a5f3fc"]),
                })
        elif self.current_scene == "Cozy Study":
            for _ in range(22):
                self.scene_elements.append({
                    "type": "rain",
                    "x": random.uniform(0, w),
                    "y": random.uniform(0, h),
                    "length": random.uniform(8.0, 16.0),
                    "vy": random.uniform(6.0, 11.0),
                    "vx": random.uniform(-1.0, -0.4),
                    "char": random.choice(["│", "┆", "💧", "·"]),
                    "color": random.choice(["#60a5fa", "#93c5fd", "#38bdf8", "#bae6fd"]),
                })
            for _ in range(6):
                self.scene_elements.append({
                    "type": "steam",
                    "x": (w - 42) + random.uniform(-6, 6),
                    "y": (h - 45) - random.uniform(10, 30),
                    "vy": random.uniform(-1.2, -0.6),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["~", "∫", "░"]),
                    "color": random.choice(["#a0aec0", "#d6d3d1", "#e2e8f0"]),
                })
        elif self.current_scene == "Sunset Beach":
            for _ in range(16):
                self.scene_elements.append({
                    "type": "wave",
                    "x": random.uniform(0, w),
                    "y": (h - 38) + random.uniform(-10, 15),
                    "vx": random.uniform(-1.2, -0.4),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["~", "≈", "≋", "·"]),
                    "color": random.choice(["#ffb703", "#fb8500", "#ffb4a2", "#ffd166", "#e07a5f"]),
                })
            for _ in range(12):
                self.scene_elements.append({
                    "type": "sparkle",
                    "x": random.uniform(10, w - 10),
                    "y": random.uniform(15, h * 0.55),
                    "vx": random.uniform(0.3, 0.8),
                    "vy": random.uniform(-0.4, 0.4),
                    "size": random.uniform(1.5, 3.5),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["✨", "✦", "🌅", "⭐"]),
                    "color": random.choice(["#ffd700", "#ffb703", "#f4a261", "#e76f51"]),
                })
        elif self.current_scene == "Rooftop Night":
            for _ in range(25):
                self.scene_elements.append({
                    "type": "city_star",
                    "x": random.uniform(5, w - 5),
                    "y": random.uniform(5, h * 0.55),
                    "size": random.uniform(1.0, 2.5),
                    "twinkle_speed": random.uniform(2.0, 5.0),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["✧", "✦", "•", "⋆", "★"]),
                    "color": random.choice(["#ffffff", "#c7d2fe", "#93c5fd", "#fef08a"]),
                })
            for i in range(14):
                bx = (i * (w / 14.0)) + random.uniform(2, 6)
                by = (h - 45) + random.uniform(5, 25)
                self.scene_elements.append({
                    "type": "window_light",
                    "x": bx,
                    "y": by,
                    "char": random.choice(["▪", "▫", "■"]),
                    "twinkle_speed": random.uniform(0.8, 2.2),
                    "phase": random.uniform(0, 2 * math.pi),
                    "color": random.choice(["#fef08a", "#fde047", "#67e8f9", "#cbd5e1"]),
                })
        elif self.current_scene == "Sunset Beach":
            for _ in range(16):
                self.scene_elements.append({
                    "type": "wave",
                    "x": random.uniform(0, w),
                    "y": random.uniform(h * 0.70, h - 8),
                    "vx": random.uniform(0.8, 2.0),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["🌊", "≋", "·", "≈", "░"]),
                    "color": random.choice(["#38bdf8", "#0284c7", "#7dd3fc", "#e0f2fe"]),
                })
            for _ in range(8):
                self.scene_elements.append({
                    "type": "sparkle",
                    "x": random.uniform(0, w),
                    "y": random.uniform(h * 0.35, h * 0.68),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["✨", "🌅", "✧", "☼"]),
                    "color": random.choice(["#fbbf24", "#f59e0b", "#fde68a", "#f43f5e"]),
                })
        elif self.current_scene == "Rooftop Night":
            self.scene_elements = []
            buildings = [
                (10, 60, 50), (65, 80, 45), (115, 110, 55),
                (175, 70, 40), (220, 95, 60), (285, 65, 45), (335, 120, 50),
            ]
            for bx, bh, bw in buildings:
                self.scene_elements.append({
                    "type": "building",
                    "x": bx,
                    "h": bh,
                    "w": bw,
                })
            for _ in range(25):
                self.scene_elements.append({
                    "type": "city_star",
                    "x": random.uniform(8, w - 8),
                    "y": random.uniform(8, h * 0.55),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["✦", "✧", "⋆", "•"]),
                    "color": random.choice(["#ffffff", "#e0e7ff", "#93c5fd", "#c7d2fe"]),
                })
        elif self.current_scene == "Sunset Beach":
            for _ in range(16):
                self.scene_elements.append({
                    "type": "wave",
                    "x": random.uniform(0, w),
                    "y": (h - 38) + random.uniform(-10, 15),
                    "vx": random.uniform(-1.2, -0.4),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["~", "≈", "≋", "·"]),
                    "color": random.choice(["#ffb703", "#fb8500", "#ffb4a2", "#ffd166", "#e07a5f"]),
                })
            for _ in range(12):
                self.scene_elements.append({
                    "type": "sparkle",
                    "x": random.uniform(10, w - 10),
                    "y": random.uniform(15, h * 0.55),
                    "vx": random.uniform(0.3, 0.8),
                    "vy": random.uniform(-0.4, 0.4),
                    "size": random.uniform(1.5, 3.5),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["✨", "✦", "🌅", "⭐"]),
                    "color": random.choice(["#ffd700", "#ffb703", "#f4a261", "#e76f51"]),
                })
        elif self.current_scene == "Rooftop Night":
            for _ in range(25):
                self.scene_elements.append({
                    "type": "city_star",
                    "x": random.uniform(5, w - 5),
                    "y": random.uniform(5, h * 0.55),
                    "size": random.uniform(1.0, 2.5),
                    "twinkle_speed": random.uniform(2.0, 5.0),
                    "phase": random.uniform(0, 2 * math.pi),
                    "char": random.choice(["✧", "✦", "•", "⋆", "★"]),
                    "color": random.choice(["#ffffff", "#c7d2fe", "#93c5fd", "#fef08a"]),
                })
            for i in range(14):
                bx = (i * (w / 14.0)) + random.uniform(2, 6)
                by = (h - 45) + random.uniform(5, 25)
                self.scene_elements.append({
                    "type": "window_light",
                    "x": bx,
                    "y": by,
                    "char": random.choice(["▪", "▫", "■"]),
                    "twinkle_speed": random.uniform(0.8, 2.2),
                    "phase": random.uniform(0, 2 * math.pi),
                    "color": random.choice(["#fef08a", "#fde047", "#67e8f9", "#cbd5e1"]),
                })

        self.scene_particles = self.scene_elements

    init_scene_particles = init_scene_elements

    def update_and_draw_scene_elements(self, t):
        """Updates and renders ambient background elements behind Mia."""
        self.canvas.delete("scene_bg")
        self.canvas.delete("bg_scene")
        w = self.canvas_w
        h = self.canvas_h
        now = time.time()

        if self.current_scene == "Sakura Park":
            for p in self.scene_elements:
                p["phase"] += 0.05
                p["x"] += p["vx"] + math.sin(p["phase"]) * 1.0
                p["y"] += p["vy"]
                if p["y"] > h:
                    p["y"] = -10
                    p["x"] = random.uniform(0, w * 0.7)
                if p["x"] > w:
                    p["x"] = -10

                rx = p["size"] * (0.8 + 0.4 * math.sin(p["phase"]))
                ry = p["size"] * (0.6 + 0.3 * math.cos(p["phase"]))
                self.canvas.create_oval(
                    p["x"] - rx, p["y"] - ry, p["x"] + rx, p["y"] + ry,
                    fill=p["color"], outline="", tags=("bg_scene", "scene_bg")
                )
                self.canvas.create_text(
                    p["x"], p["y"], text=p.get("char", "🌸"),
                    font=("DejaVu Sans", max(7, int(p["size"] * 1.8))),
                    fill=p["color"], tags=("bg_scene", "scene_bg")
                )

        elif self.current_scene == "Midnight Stars":
            moon_x, moon_y = w - 40, 36
            self.canvas.create_text(
                moon_x, moon_y, text="🌙",
                font=("DejaVu Sans", 22),
                fill="#fef08a", tags=("bg_scene", "scene_bg")
            )

            for s in self.scene_elements:
                twinkle = (math.sin(t * s["twinkle_speed"] + s["phase"]) + 1.0) / 2.0
                if twinkle > 0.20:
                    font_size = max(6, int(s["size"] * (0.8 + 0.6 * twinkle) * 2.5))
                    self.canvas.create_text(
                        s["x"], s["y"], text=s["char"],
                        font=("DejaVu Sans", font_size),
                        fill=s["color"], tags=("bg_scene", "scene_bg")
                    )

            if self.shooting_star is None:
                if now - self.last_shooting_star_time > 4.5 and random.random() < 0.25:
                    self.shooting_star = {
                        "x": random.uniform(20, w * 0.6),
                        "y": random.uniform(10, h * 0.35),
                        "vx": random.uniform(9.0, 15.0),
                        "vy": random.uniform(4.5, 8.0),
                        "life": 1.0,
                    }
                    self.last_shooting_star_time = now
            else:
                m = self.shooting_star
                m["x"] += m["vx"]
                m["y"] += m["vy"]
                m["life"] -= 0.05
                tail_x = m["x"] - m["vx"] * 2.2
                tail_y = m["y"] - m["vy"] * 2.2
                self.canvas.create_line(
                    tail_x, tail_y, m["x"], m["y"],
                    fill="#ffffff", width=2, tags=("bg_scene", "scene_bg")
                )
                self.canvas.create_text(
                    m["x"], m["y"], text="彡★",
                    font=("DejaVu Sans", 10, "bold"),
                    fill="#ffd700", tags=("bg_scene", "scene_bg")
                )
                if m["life"] <= 0 or m["x"] > w or m["y"] > h:
                    self.shooting_star = None

        elif self.current_scene == "Cozy Study":
            lamp_x, lamp_y = 45, 45
            self.canvas.create_oval(
                lamp_x - 30, lamp_y - 25, lamp_x + 30, lamp_y + 25,
                fill="#3a2518", outline="#523420", tags=("bg_scene", "scene_bg")
            )
            self.canvas.create_text(
                lamp_x, lamp_y, text="💡",
                font=("DejaVu Sans", 18),
                fill="#ffd166", tags=("bg_scene", "scene_bg")
            )

            mug_x, mug_y = w - 42, h - 45
            self.canvas.create_text(
                mug_x, mug_y, text="☕",
                font=("DejaVu Sans", 16),
                tags=("bg_scene", "scene_bg")
            )
            for i in range(3):
                s_phase = t * 3.0 + i * 1.5
                sx = mug_x + math.sin(s_phase) * 3.0
                sy = mug_y - 12 - ((s_phase * 6.0) % 20.0)
                self.canvas.create_text(
                    sx, sy, text="~",
                    font=("DejaVu Sans", 9, "bold"),
                    fill="#a0aec0", tags=("bg_scene", "scene_bg")
                )

            for r in self.scene_elements:
                if r["type"] == "rain":
                    r["y"] += r["vy"]
                    r["x"] += r["vx"]
                    if r["y"] > h:
                        r["y"] = -15
                        r["x"] = random.uniform(0, w)
                    self.canvas.create_line(
                        r["x"], r["y"], r["x"] + r["vx"] * 2, r["y"] + r["length"],
                        fill=r["color"], width=1, tags=("bg_scene", "scene_bg")
                    )
                    self.canvas.create_text(
                        r["x"], r["y"], text=r.get("char", "💧"),
                        font=("DejaVu Sans", 8),
                        fill=r["color"], tags=("bg_scene", "scene_bg")
                    )
                elif r["type"] == "steam":
                    r["y"] += r["vy"]
                    r["x"] += math.sin(t * 3.0 + r["phase"]) * 0.5
                    if r["y"] < h - 70:
                        r["y"] = h - 45
                        r["x"] = (w - 42) + random.uniform(-6, 6)
                    self.canvas.create_text(
                        r["x"], r["y"], text=r.get("char", "~"),
                        font=("DejaVu Sans", 10, "bold"),
                        fill=r["color"], tags=("bg_scene", "scene_bg")
                    )

        elif self.current_scene == "Sunset Beach":
            sun_x, sun_y = w * 0.5, 45
            self.canvas.create_oval(
                sun_x - 30, sun_y - 25, sun_x + 30, sun_y + 25,
                fill="#ff7b00", outline="#ffb703", width=2, tags=("bg_scene", "scene_bg")
            )
            self.canvas.create_text(
                sun_x, sun_y, text="🌅",
                font=("DejaVu Sans", 22),
                fill="#ffd166", tags=("bg_scene", "scene_bg")
            )

            # Rolling ocean wave lines at bottom
            for wave_y in (h - 25, h - 14):
                wave_line = "~ " * (int(w / 12) + 2)
                self.canvas.create_text(
                    w / 2.0 + math.sin(t * 3.0 + wave_y) * 8.0, wave_y,
                    text=wave_line,
                    font=("DejaVu Sans", 11, "bold"),
                    fill="#e07a5f", tags=("bg_scene", "scene_bg")
                )

            for p in self.scene_elements:
                if p["type"] == "wave":
                    p["x"] += p["vx"]
                    p["phase"] += 0.08
                    if p["x"] < -10:
                        p["x"] = w + 10
                    p_y = p["y"] + math.sin(p["phase"]) * 3.0
                    self.canvas.create_text(
                        p["x"], p_y, text=p["char"],
                        font=("DejaVu Sans", 10),
                        fill=p["color"], tags=("bg_scene", "scene_bg")
                    )
                elif p["type"] == "sparkle":
                    p["x"] += p["vx"]
                    p["y"] += p["vy"] + math.sin(t * 2.0 + p["phase"]) * 0.4
                    if p["x"] > w + 10:
                        p["x"] = -10
                    self.canvas.create_text(
                        p["x"], p["y"], text=p["char"],
                        font=("DejaVu Sans", max(8, int(p["size"] * 2.0))),
                        fill=p["color"], tags=("bg_scene", "scene_bg")
                    )

        elif self.current_scene == "Rooftop Night":
            skyline_y = h - 35
            self.canvas.create_rectangle(
                0, skyline_y, w, h,
                fill="#080711", outline="#1e1833", tags=("bg_scene", "scene_bg")
            )
            self.canvas.create_text(
                w - 35, 30, text="🌃",
                font=("DejaVu Sans", 20),
                tags=("bg_scene", "scene_bg")
            )

            for p in self.scene_elements:
                if p["type"] == "city_star":
                    twinkle = (math.sin(t * p["twinkle_speed"] + p["phase"]) + 1.0) / 2.0
                    if twinkle > 0.15:
                        self.canvas.create_text(
                            p["x"], p["y"], text=p["char"],
                            font=("DejaVu Sans", max(6, int(p["size"] * (0.8 + 0.5 * twinkle) * 2.0))),
                            fill=p["color"], tags=("bg_scene", "scene_bg")
                        )
                elif p["type"] == "window_light":
                    twinkle = (math.sin(t * p["twinkle_speed"] + p["phase"]) + 1.0) / 2.0
                    if twinkle > 0.3:
                        self.canvas.create_text(
                            p["x"], p["y"], text=p["char"],
                            font=("DejaVu Sans", 8, "bold"),
                            fill=p["color"], tags=("bg_scene", "scene_bg")
                        )

        self.canvas.tag_lower("bg_scene")
        self.canvas.tag_lower("scene_bg")

    update_scene_effects = update_and_draw_scene_elements

    def toggle_sound(self):
        """Toggles audio chime / bell option."""
        self.sound_enabled = not self.sound_enabled
        if hasattr(self, "sound_btn") and self.sound_btn:
            if self.sound_enabled:
                self.sound_btn.config(text="🔔 Chime: ON", fg="#ffd166", bg="#2c1e38")
                self.play_chime()
            else:
                self.sound_btn.config(text="🔕 Chime: OFF", fg="#8c7d9a", bg="#1e1828")

    def play_chime(self, sound_type="GREETING"):
        """Emits an expressive procedural 8-bit retro sound effect when sound is enabled."""
        if not self.sound_enabled:
            return
        played = False
        if synth_play_chime is not None:
            try:
                st = sound_type
                if isinstance(sound_type, str) and SoundType is not None:
                    upper_key = sound_type.upper()
                    if hasattr(SoundType, upper_key):
                        st = getattr(SoundType, upper_key)
                played = synth_play_chime(st)
            except Exception:
                played = False
        if not played:
            try:
                self.root.bell()
            except Exception:
                try:
                    print("\a", end="", flush=True)
                except Exception:
                    pass

    def update_study_timer_display(self):
        """Updates the focus timer display label with MM:SS."""
        mins = self.study_remaining_secs // 60
        secs = self.study_remaining_secs % 60
        timer_str = f"⏱ {mins:02d}:{secs:02d}"
        if hasattr(self, "study_timer_label") and self.study_timer_label:
            color = "#ffd166" if self.study_timer_running else "#06d6a0"
            self.study_timer_label.config(text=timer_str, fg=color)

    def toggle_study_timer(self):
        """Toggles between starting and pausing the focus timer."""
        if self.study_timer_running:
            self.pause_study_timer()
        else:
            self.start_study_timer()

    def start_study_timer(self, duration_minutes=None, subject=None):
        """Starts or resumes the focus timer countdown."""
        if duration_minutes is not None:
            self.study_duration_minutes = duration_minutes
            self.study_duration_secs = int(duration_minutes * 60)
            self.study_remaining_secs = self.study_duration_secs
        elif self.study_remaining_secs <= 0:
            self.study_remaining_secs = self.study_duration_secs

        if subject:
            self.set_study_subject(subject)

        self.study_timer_running = True
        self.study_last_tick_time = time.time()
        if hasattr(self, "btn_study_start") and self.btn_study_start:
            self.btn_study_start.config(text="⏸ Pause", fg="#ffd166", bg="#3a2518")
        self.update_study_timer_display()
        self.play_chime("CLICK")

        sub = self.study_selected_subject
        self.trigger_speech(f"Let's focus together on {sub}! You can do this! 💖📚", emotion="HAPPY")

    def pause_study_timer(self):
        """Pauses the focus timer countdown."""
        self.study_timer_running = False
        if hasattr(self, "btn_study_start") and self.btn_study_start:
            self.btn_study_start.config(text="▶ Resume", fg="#06d6a0", bg="#2c1e38")
        self.update_study_timer_display()
        self.play_chime("CLICK")

    def reset_study_timer(self, duration_minutes=None):
        """Resets the focus timer back to full duration."""
        self.study_timer_running = False
        if duration_minutes is not None:
            self.study_duration_minutes = duration_minutes
            self.study_duration_secs = int(duration_minutes * 60)
        self.study_remaining_secs = self.study_duration_secs
        if hasattr(self, "btn_study_start") and self.btn_study_start:
            self.btn_study_start.config(text="▶ Start", fg="#06d6a0", bg="#2c1e38")
        self.update_study_timer_display()
        self.play_chime("CLICK")

    def set_study_subject(self, subject: str):
        """Sets the selected study subject and updates selector."""
        self.study_selected_subject = str(subject)
        if hasattr(self, "study_subject_var") and self.study_subject_var:
            self.study_subject_var.set(self.study_selected_subject)

    def tick_study_timer(self):
        """Maintains active timer countdown, calling completion on zero."""
        if not self.study_timer_running:
            return
        now = time.time()
        elapsed = now - self.study_last_tick_time
        if elapsed >= 1.0:
            secs_passed = int(elapsed)
            self.study_last_tick_time += secs_passed
            self.study_remaining_secs = max(0, self.study_remaining_secs - secs_passed)
            self.update_study_timer_display()
            if self.study_remaining_secs <= 0:
                self.complete_study_session()

    def complete_study_session(self):
        """Triggered upon successful completion of a focus session."""
        self.study_timer_running = False
        if hasattr(self, "btn_study_start") and self.btn_study_start:
            self.btn_study_start.config(text="▶ Start", fg="#06d6a0", bg="#2c1e38")
        self.update_study_timer_display()

        duration_mins = max(1, self.study_duration_secs // 60)
        db_p = self.dialogue_engine.db_path if self.dialogue_engine else None

        if log_study_session is not None:
            try:
                log_study_session(
                    subject=self.study_selected_subject,
                    duration_minutes=duration_mins,
                    completed=True,
                    db_path=db_p,
                )
            except Exception:
                pass

        # Trigger celebratory action and particles
        self.trigger_action("CELEBRATING")
        self.spawn_particles("CONFETTI", count=25)

        # Play study bell and victory fanfare sound
        self.play_chime("STUDY_BELL")
        if hasattr(self, "root") and self.root:
            self.root.after(700, lambda: self.play_chime("CELEBRATE"))

        # Refresh stats and update badge
        self.refresh_study_stats()

        # Update friendship display
        if hasattr(self, "dialogue_engine") and self.dialogue_engine:
            self.friendship_level = self.dialogue_engine.get_friendship_level()
            self.update_friendship_display()

        congrats_msg = (
            f"🎉 Amazing focus! You finished {duration_mins}m of {self.study_selected_subject}! "
            f"I'm so proud of you! (+5 friendship) 💖🎓"
        )
        self.trigger_speech(congrats_msg, emotion="HAPPY")

    def refresh_study_stats(self):
        """Queries database for updated study streak and total minutes."""
        db_p = self.dialogue_engine.db_path if self.dialogue_engine else None
        if get_study_stats is not None:
            try:
                stats = get_study_stats(db_p)
                self.study_streak_days = stats.get("current_streak_days", 0)
                self.study_total_minutes = stats.get("total_minutes", 0)
                self.study_completed_sessions = stats.get("completed_sessions", 0)
            except Exception:
                pass
        if hasattr(self, "study_streak_label") and self.study_streak_label:
            self.study_streak_label.config(
                text=f"🔥 {self.study_streak_days}d streak • {self.study_total_minutes}m"
            )

    def update_friendship_display(self, level=None):
        """Updates the friendship level indicator and badge."""
        if level is not None:
            self.friendship_level = level
        rank_title, badge = get_friendship_rank(self.friendship_level)
        if hasattr(self, "friendship_label") and self.friendship_label:
            self.friendship_label.config(
                text=f"♥ Level {self.friendship_level} • {rank_title} {badge}"
            )

    def build_ui(self):
        tk = self.tk
        
        # Header title
        header_frame = tk.Frame(self.root, bg="#14111d")
        header_frame.pack(fill="x", pady=(8, 0))
        
        title = tk.Label(
            header_frame,
            text="✨ ✿ Princess Mia ✿ ✨",
            font=("DejaVu Sans", 14, "bold"),
            fg="#ff69b4",
            bg="#14111d"
        )
        title.pack()
        
        subtitle = tk.Label(
            header_frame,
            text="Your Interactive Pixel Companion",
            font=("DejaVu Sans", 9),
            fg="#b09fc0",
            bg="#14111d"
        )
        subtitle.pack()

        # Top Bar: Friendship Indicator & Audio Chime Toggle
        top_bar = tk.Frame(self.root, bg="#191524", padx=12, pady=5)
        top_bar.pack(fill="x", padx=16, pady=(6, 2))

        rank_title, badge = get_friendship_rank(self.friendship_level)
        self.friendship_label = tk.Label(
            top_bar,
            text=f"♥ Level {self.friendship_level} • {rank_title} {badge}",
            font=("DejaVu Sans", 9, "bold"),
            fg="#ff85c0",
            bg="#191524"
        )
        self.friendship_label.pack(side="left")

        self.sound_btn = tk.Button(
            top_bar,
            text="🔔 Chime: ON" if self.sound_enabled else "🔕 Chime: OFF",
            command=self.toggle_sound,
            font=("DejaVu Sans", 8, "bold"),
            bg="#2c1e38" if self.sound_enabled else "#1e1828",
            fg="#ffd166" if self.sound_enabled else "#8c7d9a",
            activebackground="#ff69b4",
            activeforeground="#ffffff",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2"
        )
        self.sound_btn.pack(side="right")

        # Top ML Status & Active Learning Feedback Bar
        ml_bar = tk.Frame(self.root, bg="#161224", padx=12, pady=4)
        ml_bar.pack(fill="x", padx=16, pady=(0, 2))

        init_badge = format_ml_badge(self.ml_intent, self.ml_intent_confidence, self.ml_emotion, self.ml_confidence)
        init_aura = get_aura_properties(self.ml_confidence)["title"]
        self.ml_badge_label = tk.Label(
            ml_bar,
            text=f"🤖 ML: {init_badge} • Aura: {init_aura}",
            font=("DejaVu Sans", 8, "bold"),
            fg="#70d6ff",
            bg="#161224"
        )
        self.ml_badge_label.pack(side="left")

        # Feedback controls on right side of ML bar
        fb_frame = tk.Frame(ml_bar, bg="#161224")
        fb_frame.pack(side="right")

        fb_lbl = tk.Label(
            fb_frame,
            text="Feedback:",
            font=("DejaVu Sans", 7, "bold"),
            fg="#8c7d9a",
            bg="#161224"
        )
        fb_lbl.pack(side="left", padx=(0, 4))

        self.thumb_up_btn = tk.Button(
            fb_frame,
            text="👍 Correct",
            command=lambda: self.log_feedback(True),
            font=("DejaVu Sans", 7, "bold"),
            bg="#2c1e38",
            fg="#70d6ff",
            activebackground="#06d6a0",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2"
        )
        self.thumb_up_btn.pack(side="left", padx=2)

        self.thumb_down_btn = tk.Button(
            fb_frame,
            text="👎 Wrong",
            command=lambda: self.log_feedback(False),
            font=("DejaVu Sans", 7, "bold"),
            bg="#2c1e38",
            fg="#ff70a6",
            activebackground="#ef476f",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2"
        )
        self.thumb_down_btn.pack(side="left", padx=2)

        self.feedback_label = tk.Label(
            fb_frame,
            text="",
            font=("DejaVu Sans", 7),
            fg="#a7c957",
            bg="#161224"
        )
        self.feedback_label.pack(side="left", padx=(4, 0))

        # Theme Switcher Bar
        theme_bar = tk.Frame(self.root, bg="#14111d", padx=12, pady=2)
        theme_bar.pack(fill="x", padx=16, pady=(0, 2))

        theme_lbl = tk.Label(
            theme_bar,
            text="👗 Outfit:",
            font=("DejaVu Sans", 8, "bold"),
            fg="#8c7d9a",
            bg="#14111d"
        )
        theme_lbl.pack(side="left", padx=(0, 6))

        theme_buttons_data = [
            ("Princess Pink", "🌸 Pink"),
            ("Midnight Violet", "🔮 Violet"),
            ("Golden Sunset", "🌅 Sunset"),
        ]

        for theme_key, btn_text in theme_buttons_data:
            is_active = (theme_key == self.current_theme)
            btn = tk.Button(
                theme_bar,
                text=btn_text,
                command=lambda k=theme_key: self.set_theme(k),
                font=("DejaVu Sans", 8, "bold"),
                bg="#d81b60" if is_active else "#2c1e38",
                fg="#ffffff" if is_active else "#c0adc8",
                activebackground="#ff4081",
                activeforeground="#ffffff",
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2"
            )
            btn.pack(side="left", padx=3)
            self.theme_buttons[theme_key] = btn

        # Scene Switcher Bar
        scene_bar = tk.Frame(self.root, bg="#14111d", padx=12, pady=2)
        scene_bar.pack(fill="x", padx=16, pady=(0, 2))

        scene_lbl = tk.Label(
            scene_bar,
            text="🌄 Scene:",
            font=("DejaVu Sans", 8, "bold"),
            fg="#8c7d9a",
            bg="#14111d"
        )
        scene_lbl.pack(side="left", padx=(0, 6))

        scene_buttons_data = [
            ("Sakura Park", "🌸 Sakura"),
            ("Midnight Stars", "🌙 Stars"),
            ("Cozy Study", "☕ Study"),
            ("Sunset Beach", "🌅 Beach"),
            ("Rooftop Night", "🌃 Rooftop"),
        ]

        for scene_key, btn_text in scene_buttons_data:
            is_active = (scene_key == self.current_scene)
            btn = tk.Button(
                scene_bar,
                text=btn_text,
                command=lambda k=scene_key: self.set_scene(k),
                font=("DejaVu Sans", 8, "bold"),
                bg="#d81b60" if is_active else "#2c1e38",
                fg="#ffffff" if is_active else "#c0adc8",
                activebackground="#ff4081",
                activeforeground="#ffffff",
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2"
            )
            btn.pack(side="left", padx=3)
            self.scene_buttons[scene_key] = btn

        self.btn_scene_sakura = self.scene_buttons.get("Sakura Park")
        self.btn_scene_midnight = self.scene_buttons.get("Midnight Stars")
        self.btn_scene_study = self.scene_buttons.get("Cozy Study")
        self.btn_scene_beach = self.scene_buttons.get("Sunset Beach")
        self.btn_scene_rooftop = self.scene_buttons.get("Rooftop Night")

        # Study Buddy / Pomodoro Focus Bar
        study_bar = tk.Frame(self.root, bg="#161224", padx=12, pady=2)
        study_bar.pack(fill="x", padx=16, pady=(0, 2))

        study_lbl = tk.Label(
            study_bar,
            text="📚 Focus:",
            font=("DejaVu Sans", 8, "bold"),
            fg="#ffd166",
            bg="#161224"
        )
        study_lbl.pack(side="left", padx=(0, 4))

        mins = self.study_remaining_secs // 60
        secs = self.study_remaining_secs % 60
        self.study_timer_label = tk.Label(
            study_bar,
            text=f"⏱ {mins:02d}:{secs:02d}",
            font=("DejaVu Sans", 8, "bold"),
            fg="#06d6a0",
            bg="#161224"
        )
        self.study_timer_label.pack(side="left", padx=4)

        self.study_subject_var = tk.StringVar(value=self.study_selected_subject)
        self.study_subject_menu = tk.OptionMenu(
            study_bar,
            self.study_subject_var,
            *self.study_subjects,
            command=self.set_study_subject
        )
        self.study_subject_menu.config(
            bg="#2c1e38", fg="#c0adc8", activebackground="#ff69b4",
            activeforeground="#ffffff", font=("DejaVu Sans", 7, "bold"),
            relief="flat", highlightthickness=0, bd=0
        )
        self.study_subject_menu.pack(side="left", padx=3)

        self.btn_study_start = tk.Button(
            study_bar,
            text="▶ Start",
            command=self.toggle_study_timer,
            font=("DejaVu Sans", 7, "bold"),
            bg="#2c1e38",
            fg="#06d6a0",
            activebackground="#06d6a0",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2"
        )
        self.btn_study_start.pack(side="left", padx=2)

        self.btn_study_reset = tk.Button(
            study_bar,
            text="⏹ Reset",
            command=self.reset_study_timer,
            font=("DejaVu Sans", 7, "bold"),
            bg="#2c1e38",
            fg="#ff70a6",
            activebackground="#ef476f",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2"
        )
        self.btn_study_reset.pack(side="left", padx=2)

        self.study_streak_label = tk.Label(
            study_bar,
            text=f"🔥 {self.study_streak_days}d streak • {self.study_total_minutes}m",
            font=("DejaVu Sans", 7, "bold"),
            fg="#f77f00",
            bg="#161224"
        )
        self.study_streak_label.pack(side="right")
        
        # Pixel Art Canvas
        canvas_bg = get_scene_data(self.current_scene)["bg_color"]
        self.canvas = tk.Canvas(
            self.root,
            width=self.canvas_w,
            height=self.canvas_h,
            bg=canvas_bg,
            highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=2)
        
        # Interactive Control Panel
        panel = tk.Frame(self.root, bg="#1a1626", padx=14, pady=8)
        panel.pack(fill="x", padx=16, pady=(0, 8))
        
        # Quick action greeting & physical animation buttons
        btn_frame = tk.Frame(panel, bg="#1a1626")
        btn_frame.pack(fill="x", pady=(0, 6))
        
        btn_style = {
            "bg": "#2c1e38",
            "fg": "#ffb6d9",
            "activebackground": "#ff69b4",
            "activeforeground": "#ffffff",
            "relief": "flat",
            "font": ("DejaVu Sans", 8, "bold"),
            "padx": 6,
            "pady": 3,
            "cursor": "hand2"
        }
        
        say_hello_btn = tk.Button(
            btn_frame,
            text="💬 Hello!",
            command=lambda: self.handle_user_input("hello"),
            **btn_style
        )
        say_hello_btn.pack(side="left", padx=2)
        
        wave_btn = tk.Button(
            btn_frame,
            text="👋 Wave",
            command=lambda: (self.trigger_action("WAVING"), self.handle_user_input("Wave hello! 👋")),
            **btn_style
        )
        wave_btn.pack(side="left", padx=2)

        jump_btn = tk.Button(
            btn_frame,
            text="🚀 Jump!",
            command=lambda: (self.trigger_action("JUMPING"), self.handle_user_input("Yay, jump for joy! 🚀")),
            **btn_style
        )
        jump_btn.pack(side="left", padx=2)

        blush_btn = tk.Button(
            btn_frame,
            text="💖 Blush",
            command=lambda: (self.trigger_action("BLUSHING"), self.handle_user_input("You're so cute and sweet! 💕")),
            **btn_style
        )
        blush_btn.pack(side="left", padx=2)

        celeb_btn = tk.Button(
            btn_frame,
            text="🎉 Celebrate",
            command=lambda: (self.trigger_action("CELEBRATING"), self.handle_user_input("Let's celebrate! 🎉")),
            **btn_style
        )
        celeb_btn.pack(side="left", padx=2)

        kiss_btn = tk.Button(
            btn_frame,
            text="💋 Kiss",
            command=lambda: (self.trigger_action("KISSING"), self.handle_user_input("Mwah! Sending you a sweet kiss! 💋")),
            **btn_style
        )
        kiss_btn.pack(side="left", padx=2)

        dance_btn = tk.Button(
            btn_frame,
            text="💃 Dance",
            command=lambda: (self.trigger_action("DANCING"), self.handle_user_input("Dance with me! 💃✨")),
            **btn_style
        )
        dance_btn.pack(side="left", padx=2)

        nap_btn = tk.Button(
            btn_frame,
            text="💤 Nap",
            command=lambda: (self.trigger_action("SLEEPING"), self.handle_user_input("Let's take a cozy nap together! 💤")),
            **btn_style
        )
        nap_btn.pack(side="left", padx=2)

        status_btn = tk.Button(
            btn_frame,
            text="📊 Friendship",
            command=lambda: self.handle_user_input("what is our friendship level?"),
            **btn_style
        )
        status_btn.pack(side="left", padx=2)

        # Quick action button references
        self.btn_wave = wave_btn
        self.btn_jump = jump_btn
        self.btn_blush = blush_btn
        self.btn_twirl = celeb_btn
        self.btn_kiss = kiss_btn
        self.btn_dance = dance_btn
        self.btn_nap = nap_btn
        self.action_buttons = {
            ActionState.WAVING: wave_btn,
            ActionState.JUMPING: jump_btn,
            ActionState.BLUSHING: blush_btn,
            ActionState.CELEBRATING: celeb_btn,
            ActionState.KISSING: kiss_btn,
            ActionState.DANCING: dance_btn,
            ActionState.SLEEPING: nap_btn,
        }
        
        # Text input row
        input_frame = tk.Frame(panel, bg="#1a1626")
        input_frame.pack(fill="x")
        
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.entry_var,
            font=("DejaVu Sans", 11),
            bg="#2a233b",
            fg="#ffffff",
            insertbackground="#ff69b4",
            relief="flat",
            bd=6
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.on_send())
        
        send_btn = tk.Button(
            input_frame,
            text="Send 🌸",
            command=self.on_send,
            bg="#d81b60",
            fg="#ffffff",
            activebackground="#ff4081",
            activeforeground="#ffffff",
            relief="flat",
            font=("DejaVu Sans", 10, "bold"),
            padx=14,
            pady=4,
            cursor="hand2"
        )
        send_btn.pack(side="right")
        
        # Footer hints
        footer = tk.Label(
            self.root,
            text="Type a message & hit Enter  •  Change theme above  •  Press Esc to close",
            font=("DejaVu Sans", 8),
            fg="#7c6b90",
            bg="#14111d",
            pady=4
        )
        footer.pack()
        
        # Hotkeys
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<q>", lambda e: self.root.destroy() if not self.entry.focus_get() == self.entry else None)
        
        # Center window on screen
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2) - 20
        self.root.geometry(f"+{x}+{y}")

    def init_grid_cells(self):
        """Creates the pixel rectangle items on the canvas once."""
        self.cell_items = {}
        start_x = 20
        start_y = self.girl_y_offset
        
        for r_idx in range(self.num_rows):
            for c_idx in range(self.num_cols):
                x1 = start_x + (c_idx * self.pixel_size)
                y1 = start_y + (r_idx * self.pixel_size)
                x2 = x1 + self.pixel_size
                y2 = y1 + self.pixel_size
                item = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill="",
                    outline="",
                    tags=("girl", "pixel")
                )
                self.cell_items[(r_idx, c_idx)] = item
                
        # Draw initial character frame
        self.render_girl_frame(build_frame("OPEN", 0))

    def render_girl_frame(self, grid_lines):
        """Updates cell fills for characters that changed."""
        palette = self.current_palette
        for r_idx, line in enumerate(grid_lines):
            for c_idx, char in enumerate(line):
                color = palette.get(char)
                hex_col = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}" if color else ""
                item = self.cell_items.get((r_idx, c_idx))
                if item:
                    current_fill = self.canvas.itemcget(item, "fill")
                    if current_fill != hex_col:
                        self.canvas.itemconfig(item, fill=hex_col)

    def refresh_all_cells(self):
        """Forces all canvas cells to update fill with the current palette."""
        for item in self.cell_items.values():
            self.canvas.itemconfig(item, fill="")

    def update_ml_display(self, intent: str, intent_conf: float, emotion: str, emotion_conf: float):
        """Updates the ML status badge, intent badge, aura, and feedback buttons."""
        self.ml_intent = intent
        self.ml_intent_confidence = intent_conf
        self.ml_emotion = emotion
        self.ml_confidence = emotion_conf

        aura_props = get_aura_properties(emotion_conf)
        badge_text = format_ml_badge(intent, intent_conf, emotion, emotion_conf)

        if hasattr(self, "ml_badge_label") and self.ml_badge_label:
            self.ml_badge_label.config(
                text=f"🤖 ML: {badge_text} • Aura: {aura_props['title']}"
            )
        if hasattr(self, "feedback_label") and self.feedback_label:
            self.feedback_label.config(text="")
        if hasattr(self, "thumb_up_btn") and self.thumb_up_btn:
            self.thumb_up_btn.config(text="👍 Correct", state="normal", bg="#2c1e38", fg="#70d6ff")
        if hasattr(self, "thumb_down_btn") and self.thumb_down_btn:
            self.thumb_down_btn.config(text="👎 Wrong", state="normal", bg="#2c1e38", fg="#ff70a6")

    def log_feedback(self, correct: bool, corrected_emotion=None, corrected_intent=None):
        """
        Logs active learning feedback into companion_db.
        If correct=True: logs current prediction as verified sample.
        If correct=False: logs correction to ml_dataset.
        """
        target_text = self.last_user_text or "Hello"
        target_emo = corrected_emotion or self.ml_emotion
        target_int = corrected_intent or self.ml_intent

        sample_id = None
        if add_training_sample is not None:
            try:
                db_p = self.dialogue_engine.db_path if self.dialogue_engine else None
                sample_id = add_training_sample(
                    text=target_text,
                    emotion=target_emo,
                    intent=target_int,
                    split="train",
                    source="user_feedback",
                    db_path=db_p,
                )
            except Exception:
                sample_id = None

        self.feedback_given = True
        self.play_chime()

        if correct:
            msg = "✔ Learned! 🌸"
            if hasattr(self, "thumb_up_btn") and self.thumb_up_btn:
                self.thumb_up_btn.config(text="👍 Saved", state="disabled", bg="#1b4332", fg="#a7c957")
        else:
            msg = f"Feedback noted ({target_emo}/{target_int}) ✨"
            if hasattr(self, "thumb_down_btn") and self.thumb_down_btn:
                self.thumb_down_btn.config(text="👎 Logged", state="disabled", bg="#49111c", fg="#f28482")

        if hasattr(self, "feedback_label") and self.feedback_label:
            self.feedback_label.config(text=msg)

        return True

    def draw_confidence_aura(self, cx, cy, t):
        """
        Renders the animated visual confidence aura behind Princess Mia.
        Aura intensity, color rings, and sparkle particles dynamically adapt to ML confidence.
        """
        self.canvas.delete("aura")
        if not self.aura_enabled:
            return

        conf = getattr(self, "ml_confidence", 0.85)
        props = get_aura_properties(conf)
        base_color = props["color"]
        outline_color = props["outline"]
        radius_bonus = props["radius_bonus"]

        pulse = math.sin(t * 3.0) * 4.0
        rx = (self.num_cols * self.pixel_size * 0.44) + radius_bonus + pulse
        ry = (self.num_rows * self.pixel_size * 0.46) + radius_bonus + pulse

        # Concentric glowing aura rings
        for ring_idx in (3, 2, 1):
            scale_r = 1.0 + (ring_idx * 0.08)
            x1 = cx - (rx * scale_r)
            y1 = cy - (ry * scale_r)
            x2 = cx + (rx * scale_r)
            y2 = cy + (ry * scale_r)
            width = max(1, ring_idx)
            self.canvas.create_oval(
                x1, y1, x2, y2,
                outline=outline_color if ring_idx == 1 else base_color,
                width=width,
                tags=("aura",)
            )

        # Orbiting aura sparkle particles
        particles = props["particles"]
        num_particles = 6 if conf >= 0.85 else 4
        for i in range(num_particles):
            angle = (i * (2 * math.pi / num_particles)) + (t * 1.5)
            px = cx + math.cos(angle) * (rx + 8 + math.sin(t * 4 + i) * 3)
            py = cy + math.sin(angle) * (ry + 8 + math.cos(t * 4 + i) * 3)
            p_char = particles[i % len(particles)]
            self.canvas.create_text(
                px, py,
                text=p_char,
                font=("DejaVu Sans", 9, "bold"),
                fill=base_color,
                tags=("aura",)
            )

        # Always layer aura behind the girl pixel cells
        self.canvas.tag_lower("aura", "girl")

    def trigger_action(self, action_name: str, duration: float = None) -> bool:
        """
        Triggers an expressive animated action:
        - WAVING: Waves hand cheerfully with bright smile
        - JUMPING: Realistic physics excitement jump with squash/stretch & starburst particles
        - BLUSHING: Flustered rosy cheeks with floating hearts
        - CELEBRATING: Energetic twirling celebration with starbursts and confetti
        - SLEEPING: Peaceful nap with closed eyes and floating zzZ bubbles
        - KISSING: Blown kiss with pulsing floating heart projectile
        - DANCING: Rhythmic dance sway with bouncing music notes ♪ ♫
        - IDLE: Resets to idle state
        """
        if not action_name:
            return False
        action = str(action_name).upper()
        if action not in ("WAVING", "JUMPING", "BLUSHING", "CELEBRATING", "SLEEPING", "KISSING", "DANCING", "IDLE"):
            return False

        self.action_state = action
        self.action_start_time = time.time()
        self.jump_burst_spawned = False

        default_durations = {
            "WAVING": 2.2,
            "JUMPING": 1.2,
            "BLUSHING": 2.6,
            "CELEBRATING": 2.5,
            "SLEEPING": 4.0,
            "KISSING": 2.8,
            "DANCING": 3.5,
            "IDLE": 0.0,
        }
        self.action_duration = duration if duration is not None else default_durations.get(action, 2.0)

        girl_cx = self.canvas_w / 2.0
        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0)

        if action == "JUMPING":
            self.spawn_particles("STARBURST", count=14, origin=(girl_cx, girl_cy))
            self.play_chime("JUMP")
        elif action == "CELEBRATING":
            self.spawn_particles("CONFETTI", count=16, origin=(girl_cx, girl_cy))
            self.play_chime("CELEBRATE")
        elif action == "BLUSHING":
            self.spawn_particles("HEARTS", count=10, origin=(girl_cx, girl_cy - 20))
            self.play_chime("BLUSH")
        elif action == "WAVING":
            self.play_chime("GREETING")
        elif action == "SLEEPING":
            self.spawn_particles("SLEEP_ZZZ", count=8, origin=(girl_cx + 12, girl_cy - 40))
            self.play_chime("CLICK")
        elif action == "KISSING":
            self.spawn_particles("KISS_HEARTS", count=12, origin=(girl_cx, girl_cy - 20))
            self.play_chime("BLUSH")
        elif action == "DANCING":
            self.spawn_particles("MUSIC_NOTES", count=14, origin=(girl_cx, girl_cy))
            self.play_chime("CELEBRATE")

        return True

    def show_thinking(self, prompt: str = "Thinking..."):
        """Displays the animated async thinking speech bubble."""
        self.is_thinking = True
        self.thinking_text = prompt
        self.thinking_start_time = time.time()
        self.speech_active = False
        if hasattr(self, "canvas") and self.canvas:
            self.canvas.delete("cloud")

    def hide_thinking(self):
        """Hides the async thinking speech bubble and clears it from canvas."""
        self.is_thinking = False
        if hasattr(self, "canvas") and self.canvas:
            self.canvas.delete("thinking")
            self.canvas.delete("thinking_cloud")

    def draw_thinking_cloud(self, cx: float, cy: float, scale: float = 1.0, t: float = 0.0):
        """Draws the animated thinking cloud with trailing bubbles and pulsing dots."""
        self.canvas.delete("thinking")
        self.canvas.delete("thinking_cloud")
        if not self.is_thinking:
            return

        puffs = [
            (-48, 6, 22), (-28, -12, 26), (0, -16, 28),
            (28, -12, 26), (48, 6, 22), (28, 18, 24),
            (0, 20, 26), (-28, 16, 24)
        ]
        outline_col = "#9d4edd"
        fill_col = "#201833"

        for dx, dy, r in puffs:
            x, y = cx + dx * scale, cy + dy * scale
            r_s = r * scale
            self.canvas.create_oval(
                x - r_s - 2, y - r_s - 2, x + r_s + 2, y + r_s + 2,
                fill=outline_col, outline="", tags=("thinking", "thinking_cloud")
            )

        # Thought tail trailing bubbles descending toward Mia's head
        tail_bubbles = [
            (-18 * scale, 36 * scale, 7 * scale),
            (-28 * scale, 50 * scale, 5 * scale),
            (-36 * scale, 62 * scale, 3 * scale),
        ]
        for tx, ty, tr in tail_bubbles:
            bx, by = cx + tx, cy + ty
            self.canvas.create_oval(
                bx - tr - 1, by - tr - 1, bx + tr + 1, by + tr + 1,
                fill=outline_col, outline="", tags=("thinking", "thinking_cloud")
            )
            self.canvas.create_oval(
                bx - tr, by - tr, bx + tr, by + tr,
                fill=fill_col, outline="", tags=("thinking", "thinking_cloud")
            )

        for dx, dy, r in puffs:
            x, y = cx + dx * scale, cy + dy * scale
            r_s = r * scale
            self.canvas.create_oval(
                x - r_s, y - r_s, x + r_s, y + r_s,
                fill=fill_col, outline="", tags=("thinking", "thinking_cloud")
            )

        dot_count = (int(t * 3.5) % 4)
        dots = "." * dot_count
        prompt_display = self.thinking_text.rstrip(".")
        display_text = f"✨ {prompt_display}{dots} ✨"

        self.canvas.create_text(
            cx, cy,
            text=display_text,
            font=("DejaVu Sans", max(8, int(11 * scale)), "bold"),
            fill="#e0c3fc",
            tags=("thinking", "thinking_cloud")
        )

    def spawn_particles(self, p_type="STARBURST", count=10, origin=None):
        """Spawns dynamic particles (STARBURST/JUMP, HEARTS/BLUSH, or CONFETTI/TWIRL)."""
        cx = origin[0] if origin else (self.canvas_w / 2.0)
        cy = origin[1] if origin else (self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0))
        pt = str(p_type).upper()

        if pt in ("STARBURST", "JUMP"):
            chars = ["✨", "★", "✦", "🌟", "✧", "⭐"]
            colors = ["#ffd700", "#ff69b4", "#00f0ff", "#ffffff", "#ff85a2", "#ffd166"]
            for _ in range(count):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(2.5, 7.0)
                self.particles.append({
                    "x": cx + math.cos(angle) * 15,
                    "y": cy + math.sin(angle) * 15,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed - 1.5,
                    "char": random.choice(chars),
                    "color": random.choice(colors),
                    "life": 1.0,
                    "decay": random.uniform(0.025, 0.045),
                    "type": "STARBURST",
                })
        elif pt in ("HEARTS", "HEART", "BLUSH"):
            chars = ["💖", "♥", "💕", "🌸", "💗"]
            colors = ["#ff3385", "#ff70a6", "#ffb6d9", "#ff99c8", "#ff4d6d"]
            for _ in range(count):
                self.particles.append({
                    "x": cx + random.uniform(-40, 40),
                    "y": cy + random.uniform(-20, 20),
                    "vx": random.uniform(-1.0, 1.0),
                    "vy": random.uniform(-2.5, -1.0),
                    "char": random.choice(chars),
                    "color": random.choice(colors),
                    "life": 1.0,
                    "decay": random.uniform(0.015, 0.03),
                    "type": "HEARTS",
                })
        elif pt in ("CONFETTI", "TWIRL", "CELEBRATION"):
            chars = ["🎉", "✨", "🎀", "⭐", "🌺", "■", "◆"]
            colors = ["#ff007f", "#70d6ff", "#ffd166", "#06d6a0", "#ff70a6", "#b388ff"]
            for _ in range(count):
                self.particles.append({
                    "x": cx + random.uniform(-30, 30),
                    "y": cy - 10,
                    "vx": random.uniform(-3.5, 3.5),
                    "vy": random.uniform(-6.0, -2.5),
                    "char": random.choice(chars),
                    "color": random.choice(colors),
                    "life": 1.0,
                    "decay": random.uniform(0.02, 0.035),
                    "type": "CONFETTI",
                })
        elif pt in ("SLEEP_ZZZ", "ZZZ", "SLEEP", "NAP"):
            chars = ["z", "Z", "💤", "zzZ", "•"]
            colors = ["#a5b4fc", "#c7d2fe", "#e0e7ff", "#f1f5f9", "#93c5fd"]
            for _ in range(count):
                self.particles.append({
                    "x": cx + random.uniform(-10, 20),
                    "y": cy - random.uniform(10, 30),
                    "vx": random.uniform(0.3, 1.2),
                    "vy": random.uniform(-1.8, -0.7),
                    "char": random.choice(chars),
                    "color": random.choice(colors),
                    "life": 1.0,
                    "decay": random.uniform(0.012, 0.024),
                    "type": "SLEEP_ZZZ",
                })
        elif pt in ("KISS_HEARTS", "KISS", "HEART_PROJECTILE"):
            chars = ["💋", "💖", "💕", "💘", "✨"]
            colors = ["#ff0055", "#ff2a85", "#ff70a6", "#ffb6d9", "#ffffff"]
            for _ in range(count):
                self.particles.append({
                    "x": cx + random.uniform(-15, 15),
                    "y": cy + random.uniform(-10, 10),
                    "vx": random.uniform(-2.2, 2.2),
                    "vy": random.uniform(-3.5, -1.2),
                    "char": random.choice(chars),
                    "color": random.choice(colors),
                    "life": 1.0,
                    "decay": random.uniform(0.015, 0.030),
                    "type": "KISS_HEARTS",
                })
        elif pt in ("MUSIC_NOTES", "MUSIC", "NOTES", "DANCE"):
            chars = ["♪", "♫", "♬", "♩", "✨", "🌸"]
            colors = ["#ffd166", "#06d6a0", "#118ab2", "#ef476f", "#ff99c8", "#b388ff"]
            for _ in range(count):
                self.particles.append({
                    "x": cx + random.uniform(-40, 40),
                    "y": cy + random.uniform(-20, 20),
                    "vx": random.uniform(-1.5, 1.5),
                    "vy": random.uniform(-2.8, -1.0),
                    "char": random.choice(chars),
                    "color": random.choice(colors),
                    "life": 1.0,
                    "decay": random.uniform(0.015, 0.032),
                    "type": "MUSIC_NOTES",
                })
        self.action_particles = self.particles

    def draw_particles(self, dt: float = 0.033):
        """Helper alias to update and render particles."""
        t = time.time() - self.start_time
        self.update_and_draw_particles(t)

    def update_particles(self, dt: float = 0.033):
        """Helper alias to update and render particles."""
        t = time.time() - self.start_time
        self.update_and_draw_particles(t)

    def update_and_draw_particles(self, t):
        """Updates physics and renders all active particles."""
        self.canvas.delete("particle")
        self.canvas.delete("action_particle")
        active = []
        for p in self.particles:
            p["life"] -= p["decay"]
            if p["life"] <= 0:
                continue

            # Physics movement
            p["x"] += p["vx"]
            p["y"] += p["vy"]

            if p["type"] == "STARBURST":
                p["vx"] *= 0.94
                p["vy"] += 0.15  # gravity
            elif p["type"] == "HEARTS":
                p["vx"] = math.sin(t * 5.0 + p["x"]) * 1.2
                p["vy"] -= 0.05  # buoyant float upward
            elif p["type"] == "CONFETTI":
                p["vy"] += 0.22  # gravity
                p["vx"] *= 0.97
            elif p["type"] == "SLEEP_ZZZ":
                p["vx"] += math.sin(t * 2.5 + p["y"]) * 0.08
                p["vy"] -= 0.04  # gentle drift upward
            elif p["type"] == "KISS_HEARTS":
                p["vx"] *= 0.96
                p["vy"] *= 0.96
            elif p["type"] == "MUSIC_NOTES":
                p["vx"] = math.sin(t * 6.0 + p["y"]) * 1.5
                p["vy"] += 0.06  # gentle bounce

            font_size = max(7, int(12 * p["life"]))
            self.canvas.create_text(
                p["x"], p["y"],
                text=p["char"],
                font=("DejaVu Sans", font_size, "bold"),
                fill=p["color"],
                tags=("particle", "action_particle")
            )
            active.append(p)
        self.particles = active
        self.action_particles = self.particles

    def handle_user_input(self, user_text: str):
        """Processes user input through DialogueEngine and updates UI reactions."""
        if not user_text:
            return

        self.last_user_text = user_text
        self.feedback_given = False

        # Determine and trigger expressive physical animation action
        lower = user_text.lower()
        words = set(re.findall(r"\b\w+\b", lower))
        if words & {"jump", "crazy", "omg", "yay", "won", "awesome", "hype", "woohoo"}:
            self.trigger_action("JUMPING", duration=1.2)
        elif words & {"wave", "hello", "hi", "hey", "greet", "morning", "evening"}:
            self.trigger_action("WAVING", duration=2.2)
        elif words & {"kiss", "smooch", "mwah"}:
            self.trigger_action("KISSING", duration=2.5)
        elif words & {"dance", "party", "spin", "boogie"}:
            self.trigger_action("DANCING", duration=3.0)
        elif words & {"sleep", "nap", "tired", "bed", "goodnight", "rest"}:
            self.trigger_action("SLEEPING", duration=3.5)
        elif words & {"love", "cute", "pretty", "beautiful", "blush", "marry", "sweet", "heart"}:
            self.trigger_action("BLUSHING", duration=2.6)
        elif words & {"celebrate", "hurray", "winner", "congrats"}:
            self.trigger_action("CELEBRATING", duration=2.5)

        self.show_thinking()
        try:
            if self.dialogue_engine:
                res = self.dialogue_engine.process_message(user_text)
                reply = res["reply_text"]
                emotion = res.get("emotion", "NORMAL")
                emo_conf = res.get("emotion_confidence", 0.85)
                intent = res.get("intent", "CHAT")
                int_conf = res.get("intent_confidence", 0.85)
                friendship = res.get("friendship_level", self.friendship_level)

                self.update_friendship_display(friendship)
                self.update_ml_display(intent, int_conf, emotion, emo_conf)
                self.trigger_speech(reply, emotion=emotion)
                suggested_sound = res.get("suggested_sound", "GREETING")
                self.play_chime(suggested_sound)
            else:
                if "hello" in lower or "hi" in lower:
                    reply = "HELLO! ♥"
                    intent = "GREETING"
                    emotion = "HAPPY"
                elif "love" in lower or "cute" in lower:
                    reply = "AWH, LOVE! ♥"
                    intent = "COMPLIMENT"
                    emotion = "LOVE"
                else:
                    reply = "HELLO THERE! 💖"
                    intent = "CHAT"
                    emotion = "HAPPY"
                self.update_ml_display(intent, 0.85, emotion, 0.85)
                self.trigger_speech(reply, emotion=emotion)
                sound = "BLUSH" if emotion == "LOVE" else ("GREETING" if intent == "GREETING" else "CLICK")
                self.play_chime(sound)
        finally:
            self.hide_thinking()

    def on_send(self):
        user_text = self.entry_var.get().strip()
        self.entry_var.set("")
        self.handle_user_input(user_text)

    def trigger_speech(self, text, emotion="HAPPY"):
        """Triggers the animated speech cloud reaction with emotion expression."""
        self.speech_active = True
        self.speech_text = text
        self.speech_start_time = time.time()
        self.speech_scale = 0.05
        
        # Set expression based on emotion
        if emotion in ("HAPPY", "LOVE"):
            self.expression = "HAPPY"
        elif emotion == "SHY":
            self.expression = "HALF"
        elif emotion == "PLAYFUL":
            self.expression = "BLINK"
        else:
            self.expression = "OPEN"

    def draw_speech_cloud(self, cx, cy, scale, t):
        """Draws the animated fluffy speech cloud and bouncing letters."""
        self.canvas.delete("cloud")
        if scale <= 0.02:
            return
            
        # Cloud puff circles (relative dx, dy, radius)
        puffs = [
            (-65, 8, 32), (-45, -16, 36), (-12, -22, 42),
            (25, -20, 38), (62, -6, 34), (68, 14, 28),
            (35, 24, 34), (-5, 26, 38), (-40, 22, 34)
        ]
        
        outline_col = "#e88bb7"
        fill_col = "#ffffff"
        
        # 1. Outer outline puffs
        for dx, dy, r in puffs:
            r_s = r * scale
            x, y = cx + dx * scale, cy + dy * scale
            self.canvas.create_oval(
                x - r_s - 3, y - r_s - 3, x + r_s + 3, y + r_s + 3,
                fill=outline_col, outline="", tags="cloud"
            )
            
        # 2. Cloud tail puffs pointing to her head
        tail_puffs = [
            (-20 * scale, 40 * scale, 10 * scale),
            (-32 * scale, 58 * scale, 6 * scale)
        ]
        for tx, ty, tr in tail_puffs:
            self.canvas.create_oval(
                cx + tx - tr - 2, cy + ty - tr - 2, cx + tx + tr + 2, cy + ty + tr + 2,
                fill=outline_col, outline="", tags="cloud"
            )
            self.canvas.create_oval(
                cx + tx - tr, cy + ty - tr, cx + tx + tr, cy + ty + tr,
                fill=fill_col, outline="", tags="cloud"
            )
            
        # 3. Inner fill puffs
        for dx, dy, r in puffs:
            r_s = r * scale
            x, y = cx + dx * scale, cy + dy * scale
            self.canvas.create_oval(
                x - r_s, y - r_s, x + r_s, y + r_s,
                fill=fill_col, outline="", tags="cloud"
            )
            
        # 4. Animated wave text inside cloud
        if scale > 0.6:
            text = self.speech_text
            lines = textwrap.wrap(text, width=18) if len(text) > 16 else [text]
            letter_colors = ["#ff007f", "#e91e63", "#d81b60", "#ff4081", "#c2185b", "#9c27b0"]
            
            line_height = int(18 * scale)
            start_y = cy - ((len(lines) - 1) * line_height / 2.0)
            
            for line_idx, line in enumerate(lines):
                if len(lines) == 1 and len(line) <= 14:
                    spacing = 15 * scale
                    total_w = len(line) * spacing
                    start_x = cx - (total_w / 2.0) + (spacing / 2.0)
                    font_size = max(8, int(15 * scale))
                    for idx, ch in enumerate(line):
                        wave_offset = math.sin(t * 6.0 + idx * 0.7) * (4.0 * scale)
                        lx = start_x + (idx * spacing)
                        ly = start_y + wave_offset + (2 * scale)
                        col = letter_colors[(int(t * 4) + idx) % len(letter_colors)]
                        self.canvas.create_text(
                            lx, ly, text=ch,
                            font=("DejaVu Sans", font_size, "bold"),
                            fill=col, tags="cloud"
                        )
                else:
                    font_size = max(8, int(12 * scale))
                    bounce_offset = math.sin(t * 4.0 + line_idx) * (2.0 * scale)
                    col = letter_colors[(int(t * 3) + line_idx) % len(letter_colors)]
                    self.canvas.create_text(
                        cx, start_y + (line_idx * line_height) + bounce_offset,
                        text=line,
                        font=("DejaVu Sans", font_size, "bold"),
                        fill=col, tags="cloud"
                    )
                
            # Floating sparkles around cloud
            sparkle_angles = [0.2, 1.8, 3.4, 4.9]
            sparkle_chars = ["✦", "✧", "♥", "★"]
            for s_idx, angle in enumerate(sparkle_angles):
                s_dist = (88 + math.sin(t * 4 + s_idx) * 8) * scale
                sx = cx + math.cos(angle + t * 0.8) * s_dist
                sy = cy + math.sin(angle + t * 0.8) * s_dist * 0.6
                s_col = letter_colors[(s_idx + int(t * 3)) % len(letter_colors)]
                self.canvas.create_text(
                    sx, sy,
                    text=sparkle_chars[s_idx % len(sparkle_chars)],
                    font=("DejaVu Sans", max(7, int(11 * scale))),
                    fill=s_col,
                    tags="cloud"
                )

    def update_animation(self):
        """Main 30 FPS animation update cycle."""
        self.frame_count += 1
        now = time.time()
        t = now - self.start_time

        # 0. Study timer countdown tick
        self.tick_study_timer()
        
        # 1. Speech cloud state machine & scale interpolation
        if self.speech_active:
            speech_elapsed = now - self.speech_start_time
            if speech_elapsed < 4.5:
                # Pop up with elastic bounce
                target_scale = 1.0
                self.speech_scale += (target_scale - self.speech_scale) * 0.35
            elif speech_elapsed < 5.2:
                # Fade / shrink out
                self.speech_scale *= 0.72
            else:
                self.speech_active = False
                self.speech_scale = 0.0
                self.expression = "NORMAL"
                self.canvas.delete("cloud")
        else:
            self.speech_scale = 0.0
            
        # 2. Action state machine (WAVING, JUMPING, BLUSHING, CELEBRATING)
        arm_pose = None
        jump_legs = False
        action_face = None

        if self.action_state != "IDLE":
            action_elapsed = now - self.action_start_time
            if action_elapsed >= self.action_duration:
                self.action_state = "IDLE"
                self.action_y_shift = 0.0
            else:
                progress = action_elapsed / max(0.1, self.action_duration)
                if self.action_state == "WAVING":
                    action_face = "HAPPY"
                    wave_step = int(action_elapsed * 7) % 3
                    arm_pose = [WAVE_ARM_1, WAVE_ARM_2, WAVE_ARM_3][wave_step]
                    self.action_y_shift = 0.0
                elif self.action_state == "JUMPING":
                    phys = calculate_jump_physics(progress)
                    self.action_y_shift = phys["y_offset"]
                    action_face = "EXCITED"
                    if phys["phase"] in ("ascent", "apex", "descent"):
                        jump_legs = True
                    else:
                        jump_legs = False
                    if phys["phase"] == "apex" and not getattr(self, "jump_burst_spawned", False):
                        girl_cx = self.canvas_w / 2.0
                        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0) + self.action_y_shift
                        self.spawn_particles("STARBURST", count=12, origin=(girl_cx, girl_cy))
                        self.jump_burst_spawned = True
                elif self.action_state == "BLUSHING":
                    action_face = "BLUSH"
                    self.action_y_shift = math.sin(action_elapsed * 4.0) * 1.5
                    if int(action_elapsed * 10) % 4 == 0:
                        girl_cx = self.canvas_w / 2.0
                        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0)
                        self.spawn_particles("HEARTS", count=1, origin=(girl_cx + random.uniform(-25, 25), girl_cy - 10))
                elif self.action_state == "CELEBRATING":
                    twirl = calculate_twirl_transform(progress)
                    twirl_phase = twirl["twirl_phase"]
                    action_face = "EXCITED" if twirl_phase in (0, 2) else "HAPPY"
                    hop = -abs(math.sin(twirl["angle"])) * 16.0
                    self.action_y_shift = hop
                    jump_legs = (hop < -6.0)
                    wave_step = twirl_phase % 3
                    arm_pose = [WAVE_ARM_1, WAVE_ARM_2, WAVE_ARM_3][wave_step]
                    if int(action_elapsed * 12) % 3 == 0:
                        girl_cx = self.canvas_w / 2.0
                        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0)
                        self.spawn_particles("CONFETTI", count=2, origin=(girl_cx, girl_cy))
                elif self.action_state == "SLEEPING":
                    action_face = "SLEEPING"
                    # Gentle calm breathing motion
                    self.action_y_shift = math.sin(action_elapsed * 1.8) * 2.0
                    if int(action_elapsed * 10) % 6 == 0:
                        girl_cx = self.canvas_w / 2.0
                        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0)
                        self.spawn_particles("SLEEP_ZZZ", count=1, origin=(girl_cx + 20, girl_cy - 40))
                elif self.action_state == "KISSING":
                    action_face = "KISS"
                    # Sweet leaning kiss motion
                    self.action_y_shift = -abs(math.sin(action_elapsed * 3.5)) * 4.0
                    if int(action_elapsed * 10) % 4 == 0:
                        girl_cx = self.canvas_w / 2.0
                        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0)
                        self.spawn_particles("KISS_HEARTS", count=1, origin=(girl_cx + 10, girl_cy - 20))
                elif self.action_state == "DANCING":
                    # Energetic rhythmic dancing bounce and hand swaying
                    dance_step = int(action_elapsed * 6) % 3
                    arm_pose = [WAVE_ARM_1, WAVE_ARM_2, WAVE_ARM_3][dance_step]
                    action_face = "EXCITED" if dance_step != 1 else "HAPPY"
                    self.action_y_shift = -abs(math.sin(action_elapsed * 5.0)) * 8.0
                    jump_legs = (self.action_y_shift < -4.0)
                    if int(action_elapsed * 10) % 3 == 0:
                        girl_cx = self.canvas_w / 2.0
                        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0)
                        self.spawn_particles("MUSIC_NOTES", count=2, origin=(girl_cx, girl_cy - 10))

        # 3. Girl face expression state machine
        if action_face:
            face = action_face
        elif self.speech_active:
            if self.expression == "HAPPY":
                face = "HAPPY"
            elif self.expression == "HALF":
                face = "HALF"
            elif self.expression == "BLINK":
                face = "BLINK"
            else:
                face = "HAPPY"
        else:
            # Idle blinking (blink every 3.5 seconds)
            cycle = self.frame_count % 90
            if cycle == 80:
                face = "HALF"
            elif cycle in (81, 82, 83):
                face = "BLINK"
            elif cycle == 84:
                face = "HALF"
            else:
                face = "OPEN"
                
        # 4. Sparkle frame cycle and character frame render
        sparkle_idx = (self.frame_count // 5) % len(SPARKLE_FRAMES)
        grid = build_frame(face, sparkle_idx, arm_pose=arm_pose, jump_legs=jump_legs)
        self.render_girl_frame(grid)

        # 4.5. Render ambient background elements for current scene (petals, stars, rain)
        self.update_and_draw_scene_elements(t)
        
        # 5. Combined vertical physics movement (Idle breath + action jump/squash)
        breath_y = math.sin(t * 2.2) * 2.0
        total_y = breath_y + self.action_y_shift
        dy = total_y - self.last_girl_shift_y
        self.canvas.move("girl", 0, dy)
        self.last_girl_shift_y = total_y

        # 6. Render active particles (starbursts, hearts, confetti)
        self.update_and_draw_particles(t)

        # 7. Render visual confidence aura radiating behind girl
        girl_cx = self.canvas_w / 2.0
        girl_cy = self.girl_y_offset + (self.num_rows * self.pixel_size / 2.0) + self.last_girl_shift_y
        self.draw_confidence_aura(girl_cx, girl_cy, t)
        
        # 8. Render thinking cloud if active
        if self.is_thinking:
            cloud_bob = math.sin(t * 3.5) * 2.5
            cloud_cx = (self.canvas_w / 2.0) + 10
            cloud_cy = 58 + cloud_bob
            self.draw_thinking_cloud(cloud_cx, cloud_cy, 1.0, t)

        # 9. Render speech cloud if active
        if self.speech_active and self.speech_scale > 0.02:
            cloud_bob = math.sin(t * 3.5) * 3.5
            cloud_cx = (self.canvas_w / 2.0) + 10
            cloud_cy = 58 + cloud_bob
            self.draw_speech_cloud(cloud_cx, cloud_cy, self.speech_scale, t)
            
        self.root.after(33, self.update_animation)
        
    def run(self):
        self.root.mainloop()

# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    
    # Check flags
    if "--help" in args or "-h" in args:
        print("""
✨ ✿ Princess Mia ✿ ✨ — Interactive Pixel Art Companion

Usage:
  python3 pixel_girl.py           Launch desktop animated GUI popup
  python3 pixel_girl.py --popup   Launch desktop animated GUI popup
  python3 pixel_girl.py --theme <name> Launch with theme (Princess Pink, Midnight Violet, Golden Sunset)
  python3 pixel_girl.py --terminal Launch interactive animated terminal mode
  python3 pixel_girl.py --static   Print one-time static terminal ANSI art
  python3 pixel_girl.py --say "hi" Start with greeting cloud active
  python3 pixel_girl.py --nosound  Disable sound chime
""")
        return
        
    theme_name = "Princess Pink"
    if "--theme" in args:
        t_idx = args.index("--theme")
        if t_idx + 1 < len(args):
            raw_t = args[t_idx + 1].lower()
            if "violet" in raw_t or "purple" in raw_t:
                theme_name = "Midnight Violet"
            elif "sunset" in raw_t or "gold" in raw_t:
                theme_name = "Golden Sunset"
            else:
                theme_name = "Princess Pink"

    sound_enabled = "--nosound" not in args

    if "--static" in args:
        banner = f"\n\033[1;38;2;255;105;180m  ✨ ✿ Princess Mia ✿ ✨ [{theme_name}]\033[0m\n"
        print(banner)
        palette = get_theme_palette(theme_name)
        print(render_ansi_grid(BASE_ART, palette=palette))
        print("\n\033[38;2;255;160;200m     ♥ Pixel Art for Terminal ♥\033[0m\n")
        return

    initial_say = ("--say" in args) or any("hello" in a.lower() for a in args)

    if "--terminal" in args or "-t" in args or "--cli" in args:
        run_terminal_app(initial_greeting=initial_say, theme_name=theme_name, enable_sound=sound_enabled)
        return

    scene_name = None
    if "--scene" in args:
        s_idx = args.index("--scene")
        if s_idx + 1 < len(args):
            raw_s = args[s_idx + 1].lower()
            if "star" in raw_s or "midnight" in raw_s:
                scene_name = "Midnight Stars"
            elif "study" in raw_s or "cozy" in raw_s or "rain" in raw_s:
                scene_name = "Cozy Study"
            elif "sakura" in raw_s or "park" in raw_s:
                scene_name = "Sakura Park"

    # Check for GUI display
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if has_display:
        try:
            app = PixelGirlPopup(pixel_size=10, initial_greeting=initial_say, theme=theme_name, enable_sound=sound_enabled, scene=scene_name)
            app.run()
            return
        except Exception as e:
            print(f"Notice: Could not launch GUI ({e}). Falling back to Terminal mode...\n")
            run_terminal_app(initial_greeting=initial_say, theme_name=theme_name, enable_sound=sound_enabled)
    else:
        run_terminal_app(initial_greeting=initial_say, theme_name=theme_name, enable_sound=sound_enabled)

if __name__ == "__main__":
    main()
