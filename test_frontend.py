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
import sys
import unittest

# Ensure the worktree's own modules take precedence over parent directories
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from pixel_girl import (
    BASE_ART,
    PALETTE,
    PALETTE_GOLDEN_SUNSET,
    PALETTE_MIDNIGHT_VIOLET,
    PALETTE_PRINCESS_PINK,
    THEMES,
    PixelGirlPopup,
    format_ml_badge,
    get_aura_properties,
    get_friendship_rank,
    get_theme_palette,
    render_ansi_grid,
    build_frame,
    FACE_BLUSH,
    FACE_EXCITED,
    FACE_HAPPY,
    WAVE_ARM_1,
    WAVE_ARM_2,
    WAVE_ARM_3,
    JUMP_LEGS_OVERRIDE,
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

    def test_ml_initial_state(self):
        """PixelGirlPopup initializes ML confidence, intent, aura, and feedback buttons."""
        self.assertIsNotNone(self.app.ml_badge_label)
        self.assertIsNotNone(self.app.thumb_up_btn)
        self.assertIsNotNone(self.app.thumb_down_btn)
        self.assertIsNotNone(self.app.feedback_label)
        self.assertTrue(self.app.aura_enabled)
        self.assertTrue(0.0 <= self.app.ml_confidence <= 1.0)
        self.assertTrue(0.0 <= self.app.ml_intent_confidence <= 1.0)
        badge_txt = self.app.ml_badge_label.cget("text")
        self.assertIn("ML:", badge_txt)
        self.assertIn("Aura:", badge_txt)

    def test_update_ml_display(self):
        """update_ml_display updates intent badge, emotion percentage, and aura title."""
        self.app.update_ml_display("COMPLIMENT", 0.96, "LOVE", 0.92)
        self.assertEqual(self.app.ml_intent, "COMPLIMENT")
        self.assertEqual(self.app.ml_intent_confidence, 0.96)
        self.assertEqual(self.app.ml_emotion, "LOVE")
        self.assertEqual(self.app.ml_confidence, 0.92)

        badge_text = self.app.ml_badge_label.cget("text")
        self.assertIn("[COMPLIMENT]", badge_text)
        self.assertIn("96%", badge_text)
        self.assertIn("LOVE", badge_text)
        self.assertIn("92%", badge_text)
        self.assertIn("Radiant Gold", badge_text)

    def test_active_learning_feedback_thumbs_up(self):
        """Clicking thumbs up records user feedback sample and updates button state."""
        self.app.handle_user_input("Good morning Mia! You are so cute! 💕")
        success = self.app.log_feedback(True)
        self.assertTrue(success)
        self.assertTrue(self.app.feedback_given)
        self.assertEqual(self.app.thumb_up_btn.cget("text"), "👍 Saved")
        self.assertEqual(self.app.thumb_up_btn.cget("state"), "disabled")
        self.assertIn("Learned", self.app.feedback_label.cget("text"))

    def test_active_learning_feedback_thumbs_down(self):
        """Clicking thumbs down logs correction and updates button state."""
        self.app.handle_user_input("What is the weather outside?")
        success = self.app.log_feedback(False, corrected_emotion="NORMAL", corrected_intent="QUESTION")
        self.assertTrue(success)
        self.assertTrue(self.app.feedback_given)
        self.assertEqual(self.app.thumb_down_btn.cget("text"), "👎 Logged")
        self.assertEqual(self.app.thumb_down_btn.cget("state"), "disabled")
        self.assertIn("Feedback noted", self.app.feedback_label.cget("text"))

    def test_visual_confidence_aura_rendering(self):
        """draw_confidence_aura creates canvas items with tag 'aura'."""
        self.app.draw_confidence_aura(150, 150, 1.0)
        items = self.app.canvas.find_withtag("aura")
        self.assertGreater(len(items), 0)

    def test_confidence_aura_toggle(self):
        """Disabling aura removes or suppresses aura items."""
        self.app.aura_enabled = False
        self.app.draw_confidence_aura(150, 150, 1.0)
        items = self.app.canvas.find_withtag("aura")
        self.assertEqual(len(items), 0)
        self.app.aura_enabled = True


class TestMLBadgeAndAuraCalculations(unittest.TestCase):
    """Tests ML badge formatting and confidence aura tier calculations."""

    def test_format_ml_badge(self):
        cases = [
            ("GREETING", 0.985, "HAPPY", 0.941, "[GREETING] (98%) • Emotion: HAPPY (94%)"),
            ("COMPLIMENT", 0.850, "LOVE", 0.760, "[COMPLIMENT] (85%) • Emotion: LOVE (76%)"),
            ("CHAT", 0.500, "NORMAL", 0.600, "[CHAT] (50%) • Emotion: NORMAL (60%)"),
        ]
        for intent, int_conf, emo, emo_conf, expected in cases:
            with self.subTest(intent=intent, emo=emo):
                res = format_ml_badge(intent, int_conf, emo, emo_conf)
                self.assertEqual(res, expected)

    def test_aura_properties_tiers(self):
        high = get_aura_properties(0.95)
        self.assertEqual(high["tier"], "high")
        self.assertEqual(high["color"], "#ffd700")
        self.assertIn("Radiant Gold", high["title"])
        self.assertGreaterEqual(high["radius_bonus"], 14)

        medium = get_aura_properties(0.75)
        self.assertEqual(medium["tier"], "medium")
        self.assertEqual(medium["color"], "#00f0ff")
        self.assertIn("Celestial Glow", medium["title"])

        low = get_aura_properties(0.45)
        self.assertEqual(low["tier"], "low")
        self.assertEqual(low["color"], "#b388ff")
        self.assertIn("Soft Lavender", low["title"])


class TestActionSystemAndAnimationOverhaul(unittest.TestCase):
    """Tests action state machine, frame construction with arm/leg overrides, and particle physics."""

    def test_build_frame_dimensions(self):
        """Every built frame must maintain exact 47 rows × 40 columns across all facial and body states."""
        faces = ["OPEN", "BLINK", "HALF", "HAPPY", "EXCITED", "BLUSH"]
        for face in faces:
            frame = build_frame(face_type=face)
            self.assertEqual(len(frame), 47, f"Face {face} invalid row count")
            for r_idx, row in enumerate(frame):
                self.assertEqual(len(row), 40, f"Face {face} row {r_idx} invalid column count: {len(row)}")

    def test_waving_arm_overrides(self):
        """Waving arm overrides preserve 40-column width and modify arm rows (14..26)."""
        for arm_idx, arm_pose in enumerate([WAVE_ARM_1, WAVE_ARM_2, WAVE_ARM_3], 1):
            frame = build_frame(face_type="HAPPY", arm_pose=arm_pose)
            self.assertEqual(len(frame), 47)
            for r_idx, row in enumerate(frame):
                self.assertEqual(len(row), 40, f"Wave arm {arm_idx} row {r_idx} len != 40")
            # Row 14 contains raised waving hand patch
            self.assertIn("sSSs", frame[14])

    def test_jump_legs_override(self):
        """Jumping legs override tucks legs upward in mid-air (rows 40..46)."""
        frame = build_frame(face_type="EXCITED", jump_legs=True)
        self.assertEqual(len(frame), 47)
        for r_idx, row in enumerate(frame):
            self.assertEqual(len(row), 40, f"Jump legs row {r_idx} len != 40")
        # Row 44 and 45 become air space under shoes
        self.assertEqual(frame[44].strip(), "")
        self.assertEqual(frame[45].strip(), "")

    def test_gui_action_state_machine_and_particles(self):
        """Tests trigger_action transitions, duration, particle spawning, and keyword triggers."""
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except Exception:
            self.skipTest("Tkinter display not available")

        app = PixelGirlPopup(pixel_size=4, initial_greeting=False, enable_sound=False)
        app.root.withdraw()
        try:
            # 1. Test WAVING action
            app.trigger_action("WAVING")
            self.assertEqual(app.action_state, "WAVING")
            self.assertGreater(app.action_duration, 0)

            # 2. Test JUMPING action and starburst particles
            app.trigger_action("JUMPING")
            self.assertEqual(app.action_state, "JUMPING")
            self.assertGreater(len(app.particles), 0)
            starbursts = [p for p in app.particles if p["type"] == "STARBURST"]
            self.assertGreater(len(starbursts), 0)

            # 3. Test BLUSHING action and hearts particles
            app.trigger_action("BLUSHING")
            self.assertEqual(app.action_state, "BLUSHING")
            hearts = [p for p in app.particles if p["type"] == "HEARTS"]
            self.assertGreater(len(hearts), 0)

            # 4. Test CELEBRATING action
            app.trigger_action("CELEBRATING")
            self.assertEqual(app.action_state, "CELEBRATING")

            # 5. Test particle physics update and drawing
            app.update_and_draw_particles(1.0)
            items = app.canvas.find_withtag("particle")
            self.assertGreater(len(items), 0)

            # 6. Test keyword-based action triggering in handle_user_input
            app.handle_user_input("OMG that was crazy!")
            self.assertEqual(app.action_state, "JUMPING")

            app.handle_user_input("Wave to everyone!")
            self.assertEqual(app.action_state, "WAVING")

            app.handle_user_input("You are so sweet and I love you!")
            self.assertEqual(app.action_state, "BLUSHING")

            app.handle_user_input("Let us celebrate this win!")
            self.assertEqual(app.action_state, "CELEBRATING")
        finally:
            if app and app.root:
                app.root.destroy()


if __name__ == "__main__":
    unittest.main()
