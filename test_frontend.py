#!/usr/bin/env python3
"""
test_frontend.py — Unit Tests for Frontend UI/UX Enhancements in pixel_girl.py
Tests:
  - Theme palettes (Princess Pink, Midnight Violet, Golden Sunset) validity and completeness
  - Theme switching logic (get_theme_palette, set_theme)
  - Friendship level indicator calculations (level to rank title & badge icon)
  - Audio chime/bell toggle and execution resilience
  - Terminal theme rendering
  - GUI PixelGirlPopup component lifecycle, dialogue engine integration, and reactions
"""

import os
import unittest
from pixel_girl import (
    BASE_ART,
    PALETTE,
    PALETTE_GOLDEN_SUNSET,
    PALETTE_MIDNIGHT_VIOLET,
    PALETTE_PRINCESS_PINK,
    THEMES,
    PixelGirlPopup,
    get_friendship_rank,
    get_theme_palette,
    render_ansi_grid,
)


class TestThemePalettes(unittest.TestCase):
    """Verifies theme palette definitions, structure, and integrity."""

    def test_themes_exist(self):
        expected_themes = ["Princess Pink", "Midnight Violet", "Golden Sunset"]
        for theme_name in expected_themes:
            self.assertIn(theme_name, THEMES, f"Missing theme: {theme_name}")

    def test_palette_completeness(self):
        """Every theme palette must map all character keys present in BASE_ART and default PALETTE."""
        required_keys = set(PALETTE.keys())
        for theme_name, palette in THEMES.items():
            with self.subTest(theme=theme_name):
                for key in required_keys:
                    self.assertIn(key, palette, f"Theme '{theme_name}' missing key '{key}'")

    def test_palette_colors_valid_rgb(self):
        """Every color in all themes must be None (transparent) or a valid (0-255, 0-255, 0-255) RGB tuple."""
        for theme_name, palette in THEMES.items():
            with self.subTest(theme=theme_name):
                for key, val in palette.items():
                    if val is None:
                        continue
                    self.assertIsInstance(val, tuple, f"Color for '{key}' in '{theme_name}' is not a tuple")
                    self.assertEqual(len(val), 3, f"Color for '{key}' in '{theme_name}' does not have 3 channels")
                    for channel in val:
                        self.assertIsInstance(channel, int)
                        self.assertTrue(0 <= channel <= 255, f"Channel value {channel} out of range in {theme_name}")

    def test_get_theme_palette(self):
        self.assertEqual(get_theme_palette("Princess Pink"), PALETTE_PRINCESS_PINK)
        self.assertEqual(get_theme_palette("Midnight Violet"), PALETTE_MIDNIGHT_VIOLET)
        self.assertEqual(get_theme_palette("Golden Sunset"), PALETTE_GOLDEN_SUNSET)
        # Fallback to default
        self.assertEqual(get_theme_palette("NonExistentTheme"), PALETTE_PRINCESS_PINK)


class TestFriendshipRank(unittest.TestCase):
    """Tests friendship level to rank title and badge mapping."""

    def test_ranks_progression(self):
        cases = [
            (0, "New Friend", "✨"),
            (4, "New Friend", "✨"),
            (5, "Friendly Acquaintance", "🌱"),
            (9, "Friendly Acquaintance", "🌱"),
            (10, "Good Friend", "🌸"),
            (19, "Good Friend", "🌸"),
            (20, "Close Companion", "💖"),
            (29, "Close Companion", "💖"),
            (30, "Best Friend Forever", "👑"),
            (50, "Best Friend Forever", "👑"),
        ]
        for level, expected_title, expected_badge in cases:
            with self.subTest(level=level):
                title, badge = get_friendship_rank(level)
                self.assertEqual(title, expected_title)
                self.assertEqual(badge, expected_badge)


class TestTerminalRenderingWithThemes(unittest.TestCase):
    """Tests terminal ANSI rendering for different themes."""

    def test_render_all_themes(self):
        sample_slice = BASE_ART[:4]
        for theme_name in THEMES:
            with self.subTest(theme=theme_name):
                palette = get_theme_palette(theme_name)
                rendered = render_ansi_grid(sample_slice, palette=palette)
                self.assertIsInstance(rendered, str)
                self.assertGreater(len(rendered), 0)
                # Should contain 24-bit ANSI color escape codes
                self.assertIn("\033[38;2;", rendered)


class TestPixelGirlPopupGUI(unittest.TestCase):
    """Tests GUI initialization, theme switching, chime toggle, and dialogue integration."""

    @classmethod
    def setUpClass(cls):
        # Verify if GUI / Tkinter is available
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
            cls.gui_supported = True
        except Exception:
            cls.gui_supported = False

    def setUp(self):
        if not self.gui_supported:
            self.skipTest("Tkinter display not available in this test environment")
        self.app = PixelGirlPopup(pixel_size=4, initial_greeting=False, enable_sound=False)
        self.app.root.withdraw()  # Keep window hidden during test execution

    def tearDown(self):
        if hasattr(self, "app") and self.app and self.app.root:
            try:
                self.app.root.destroy()
            except Exception:
                pass

    def test_initial_state(self):
        self.assertEqual(self.app.current_theme, "Princess Pink")
        self.assertFalse(self.app.sound_enabled)
        self.assertIsNotNone(self.app.canvas)
        self.assertIsNotNone(self.app.friendship_label)

    def test_theme_switching(self):
        """Switching theme updates current_theme, current_palette, and cell colors."""
        self.app.set_theme("Midnight Violet")
        self.assertEqual(self.app.current_theme, "Midnight Violet")
        self.assertEqual(self.app.current_palette, PALETTE_MIDNIGHT_VIOLET)

        self.app.set_theme("Golden Sunset")
        self.assertEqual(self.app.current_theme, "Golden Sunset")
        self.assertEqual(self.app.current_palette, PALETTE_GOLDEN_SUNSET)

        self.app.set_theme("Princess Pink")
        self.assertEqual(self.app.current_theme, "Princess Pink")
        self.assertEqual(self.app.current_palette, PALETTE_PRINCESS_PINK)

    def test_sound_toggle_and_chime(self):
        """Toggling sound switches sound_enabled flag and play_chime does not throw."""
        initial = self.app.sound_enabled
        self.app.toggle_sound()
        self.assertEqual(self.app.sound_enabled, not initial)
        self.app.play_chime()  # Should not raise exception
        self.app.toggle_sound()
        self.assertEqual(self.app.sound_enabled, initial)

    def test_friendship_indicator_update(self):
        """Updating friendship display updates level and label text."""
        self.app.update_friendship_display(25)
        self.assertEqual(self.app.friendship_level, 25)
        label_text = self.app.friendship_label.cget("text")
        self.assertIn("Level 25", label_text)
        self.assertIn("Close Companion", label_text)

    def test_dialogue_engine_integration_via_handle_input(self):
        """User input passes through dialogue engine, triggers speech cloud and updates reaction."""
        self.app.handle_user_input("Good morning Mia!")
        self.assertTrue(self.app.speech_active)
        self.assertIn("Good morning", self.app.speech_text)
        self.assertEqual(self.app.expression, "HAPPY")


if __name__ == "__main__":
    unittest.main()
