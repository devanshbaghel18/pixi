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

import math
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
    SCENES,
    DEFAULT_SCENE,
    get_scene_data,
    ActionState,
    VALID_ACTIONS,
    PixelGirlPopup,
    calculate_jump_physics,
    calculate_twirl_transform,
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

    def test_action_state_constants_and_valid_actions(self):
        """ActionState must define IDLE, WAVING, JUMPING, BLUSHING, and CELEBRATING."""
        self.assertEqual(ActionState.IDLE, "IDLE")
        self.assertEqual(ActionState.WAVING, "WAVING")
        self.assertEqual(ActionState.JUMPING, "JUMPING")
        self.assertEqual(ActionState.BLUSHING, "BLUSHING")
        self.assertEqual(ActionState.CELEBRATING, "CELEBRATING")

        expected = ("IDLE", "WAVING", "JUMPING", "BLUSHING", "CELEBRATING")
        for state in expected:
            self.assertIn(state, VALID_ACTIONS)

    def test_calculate_jump_physics(self):
        """calculate_jump_physics computes squash, parabolic trajectory, apex, and landing."""
        # 1. Crouch (p = 0.05)
        crouch = calculate_jump_physics(0.05)
        self.assertEqual(crouch["phase"], "crouch")
        self.assertLess(crouch["scale_y"], 1.0)
        self.assertGreater(crouch["scale_x"], 1.0)
        self.assertGreater(crouch["y_offset"], 0.0)

        # 2. Airborne ascent (p = 0.30)
        ascent = calculate_jump_physics(0.30)
        self.assertEqual(ascent["phase"], "ascent")
        self.assertLess(ascent["y_offset"], 0.0)
        self.assertGreater(ascent["scale_y"], 1.0)

        # 3. Apex (p = 0.425)
        apex = calculate_jump_physics(0.425)
        self.assertEqual(apex["phase"], "apex")
        self.assertLess(apex["y_offset"], -35.0)

        # 4. Descent (p = 0.60)
        descent = calculate_jump_physics(0.60)
        self.assertEqual(descent["phase"], "descent")
        self.assertLess(descent["y_offset"], 0.0)

        # 5. Landing impact (p = 0.78)
        land = calculate_jump_physics(0.78)
        self.assertEqual(land["phase"], "land")
        self.assertLess(land["scale_y"], 1.0)
        self.assertGreater(land["scale_x"], 1.0)

        # 6. Recovery (p = 0.95)
        recovery = calculate_jump_physics(0.95)
        self.assertEqual(recovery["phase"], "recovery")

    def test_calculate_twirl_transform(self):
        """calculate_twirl_transform computes continuous spin angle, scale, and phases."""
        for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
            twirl = calculate_twirl_transform(p)
            self.assertIn("angle", twirl)
            self.assertIn("cos_angle", twirl)
            self.assertIn("sin_angle", twirl)
            self.assertIn("scale_x", twirl)
            self.assertIn("twirl_phase", twirl)
            self.assertIn("skirt_flare", twirl)
            self.assertTrue(0.0 <= twirl["scale_x"] <= 1.05)
            self.assertIn(twirl["twirl_phase"], (0, 1, 2, 3))

    def test_build_frame_wave_frame_numeric_parameter(self):
        """build_frame accepts wave_frame=1, 2, 3 directly to override arm rows."""
        for wf in (1, 2, 3):
            frame = build_frame(face_type="HAPPY", wave_frame=wf)
            self.assertEqual(len(frame), 47)
            self.assertIn("sSSs", frame[14])

    def test_build_frame_blush_face(self):
        """build_frame with face_type='BLUSH' includes blushing heart marks and rosy cheek rows."""
        frame = build_frame(face_type="BLUSH")
        self.assertEqual(len(frame), 47)
        face_slice = "\n".join(frame[12:18])
        self.assertIn("BBBBB", face_slice)

    def test_gui_action_state_machine_and_particles(self):
        """Tests trigger_action transitions, duration, particle spawning, and keyword triggers."""
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except Exception:
            self.skipTest("Tkinter display not available")

        app = PixelGirlPopup(pixel_size=4, initial_greeting=False, enable_sound=False, scene="Sakura Park")
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

    def test_thinking_bubble_and_quick_action_buttons(self):
        """Tests thinking bubble lifecycle, quick action button handles, and draw_particles."""
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except Exception:
            self.skipTest("Tkinter display not available")

        app = PixelGirlPopup(pixel_size=4, initial_greeting=False, enable_sound=False, scene="Sakura Park")
        app.root.withdraw()
        try:
            # 1. Quick action button attributes and dictionary
            self.assertIsNotNone(app.btn_wave)
            self.assertIsNotNone(app.btn_jump)
            self.assertIsNotNone(app.btn_blush)
            self.assertIsNotNone(app.btn_twirl)
            self.assertIn(ActionState.WAVING, app.action_buttons)
            self.assertIn(ActionState.JUMPING, app.action_buttons)
            self.assertIn(ActionState.BLUSHING, app.action_buttons)
            self.assertIn(ActionState.CELEBRATING, app.action_buttons)

            # 2. Thinking speech bubble show/hide lifecycle
            self.assertFalse(app.is_thinking)
            app.show_thinking("Contemplating...")
            self.assertTrue(app.is_thinking)
            self.assertEqual(app.thinking_text, "Contemplating...")

            app.draw_thinking_cloud(150, 60, scale=1.0, t=1.0)
            items = app.canvas.find_withtag("thinking_cloud")
            self.assertGreater(len(items), 0)

            app.hide_thinking()
            self.assertFalse(app.is_thinking)
            items_after = app.canvas.find_withtag("thinking_cloud")
            self.assertEqual(len(items_after), 0)

            # 3. Action triggering validation
            self.assertTrue(app.trigger_action(ActionState.WAVING))
            self.assertEqual(app.action_state, ActionState.WAVING)
            self.assertFalse(app.trigger_action("NOT_A_VALID_ACTION"))

            # 4. Particles and draw_particles alias
            app.spawn_particles("JUMP", count=6)
            self.assertGreater(len(app.action_particles), 0)
            app.draw_particles()
            part_items = app.canvas.find_withtag("action_particle")
            self.assertGreater(len(part_items), 0)
        finally:
            if app and app.root:
                app.root.destroy()


class TestInteractiveScenesAndEnvironments(unittest.TestCase):
    """Tests interactive environment scenes, ambient particles, and scene switcher."""

    def test_scenes_dictionary_and_data(self):
        """Verifies SCENES definitions and get_scene_data fallback."""
        expected = ["Sakura Park", "Midnight Stars", "Cozy Study"]
        for scene_name in expected:
            self.assertIn(scene_name, SCENES)
            data = get_scene_data(scene_name)
            self.assertIn("bg_color", data)
            self.assertIn("title", data)
            self.assertIn("desc", data)

        fallback = get_scene_data("NonExistentScene")
        self.assertEqual(fallback, SCENES[DEFAULT_SCENE])

    def test_gui_scene_switching_and_elements(self):
        """Tests scene switching, canvas background updates, and ambient background element rendering."""
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except Exception:
            self.skipTest("Tkinter display not available")

        app = PixelGirlPopup(pixel_size=4, initial_greeting=False, enable_sound=False, scene="Sakura Park")
        app.root.withdraw()
        try:
            # Initial scene should be Sakura Park
            self.assertEqual(app.current_scene, "Sakura Park")
            self.assertGreater(len(app.scene_elements), 0)
            self.assertEqual(app.scene_elements[0]["type"], "petal")

            # Switch to Midnight Stars
            app.set_scene("Midnight Stars")
            self.assertEqual(app.current_scene, "Midnight Stars")
            self.assertEqual(app.canvas.cget("bg"), SCENES["Midnight Stars"]["bg_color"])
            self.assertEqual(app.scene_elements[0]["type"], "star")

            # Render scene elements on canvas
            app.update_and_draw_scene_elements(1.0)
            bg_items = app.canvas.find_withtag("scene_bg")
            self.assertGreater(len(bg_items), 0)

            # Switch to Cozy Study
            app.set_scene("Cozy Study")
            self.assertEqual(app.current_scene, "Cozy Study")
            self.assertEqual(app.canvas.cget("bg"), SCENES["Cozy Study"]["bg_color"])
            self.assertEqual(app.scene_elements[0]["type"], "rain")

            app.update_and_draw_scene_elements(1.0)
            cozy_items = app.canvas.find_withtag("scene_bg")
            self.assertGreater(len(cozy_items), 0)

            # Switch back to Sakura Park
            app.set_scene("Sakura Park")
            self.assertEqual(app.current_scene, "Sakura Park")
        finally:
            if app and app.root:
                app.root.destroy()


class TestStudyBuddyAndPomodoroTimer(unittest.TestCase):
    """Tests the Study Buddy focus timer state machine, streak calculations, and completion celebration."""

    def setUp(self):
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except Exception:
            self.skipTest("Tkinter display not available")

        self.app = PixelGirlPopup(pixel_size=4, initial_greeting=False, enable_sound=False)
        self.app.root.withdraw()

    def tearDown(self):
        if self.app and self.app.root:
            self.app.root.destroy()

    def test_study_timer_initial_state(self):
        """Verifies initial Study Buddy widget attributes and timer state."""
        self.assertEqual(self.app.study_duration_minutes, 25)
        self.assertEqual(self.app.study_remaining_secs, 25 * 60)
        self.assertFalse(self.app.study_timer_running)
        self.assertEqual(self.app.study_selected_subject, "General")
        self.assertIn("General", self.app.study_subjects)
        self.assertIn("Math", self.app.study_subjects)
        self.assertIsNotNone(self.app.study_timer_label)
        self.assertIsNotNone(self.app.btn_study_start)
        self.assertIsNotNone(self.app.btn_study_reset)
        self.assertIsNotNone(self.app.study_streak_label)

    def test_study_timer_start_pause_resume_reset(self):
        """Tests start, pause, resume, and reset cycles of the focus timer."""
        # 1. Start timer
        self.app.start_study_timer(duration_minutes=25, subject="Coding")
        self.assertTrue(self.app.study_timer_running)
        self.assertEqual(self.app.study_selected_subject, "Coding")
        self.assertEqual(self.app.btn_study_start.cget("text"), "⏸ Pause")

        # 2. Pause timer
        self.app.pause_study_timer()
        self.assertFalse(self.app.study_timer_running)
        self.assertEqual(self.app.btn_study_start.cget("text"), "▶ Resume")

        # 3. Toggle resumes
        self.app.toggle_study_timer()
        self.assertTrue(self.app.study_timer_running)
        self.assertEqual(self.app.btn_study_start.cget("text"), "⏸ Pause")

        # 4. Reset timer
        self.app.reset_study_timer(duration_minutes=30)
        self.assertFalse(self.app.study_timer_running)
        self.assertEqual(self.app.study_duration_secs, 30 * 60)
        self.assertEqual(self.app.study_remaining_secs, 30 * 60)
        self.assertEqual(self.app.btn_study_start.cget("text"), "▶ Start")

    def test_study_subject_selection(self):
        """Tests changing subject modifies study_selected_subject and widget text."""
        self.app.set_study_subject("Physics")
        self.assertEqual(self.app.study_selected_subject, "Physics")
        self.assertEqual(self.app.study_subject_var.get(), "Physics")

    def test_study_timer_tick_and_countdown(self):
        """Verifies tick_study_timer decrements remaining seconds and updates display."""
        self.app.start_study_timer(duration_minutes=10, subject="Math")
        self.app.study_remaining_secs = 600
        # Simulate 3 seconds elapsed
        self.app.study_last_tick_time = self.app.study_last_tick_time - 3.5
        self.app.tick_study_timer()
        self.assertLessEqual(self.app.study_remaining_secs, 597)
        self.assertIn("09:", self.app.study_timer_label.cget("text"))

    def test_study_session_completion(self):
        """Verifies session completion triggers celebration action, particles, and speech message."""
        self.app.study_selected_subject = "AI Research"
        self.app.study_duration_secs = 1500
        self.app.study_remaining_secs = 0
        self.app.complete_study_session()

        # Should transition to CELEBRATING action state
        self.assertEqual(self.app.action_state, "CELEBRATING")
        self.assertGreater(len(self.app.action_particles), 0)
        # Should display congratulatory speech cloud
        self.assertTrue(self.app.speech_active)
        self.assertIn("AI Research", self.app.speech_text)
        self.assertIn("Amazing focus", self.app.speech_text)


class TestProceduralSoundSynthesizerWiring(unittest.TestCase):
    """Tests the integration of procedural 8-bit sound effects into frontend components."""

    def setUp(self):
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except Exception:
            self.skipTest("Tkinter display not available")

        self.app = PixelGirlPopup(pixel_size=4, initial_greeting=False, enable_sound=True)
        self.app.root.withdraw()

    def tearDown(self):
        if self.app and self.app.root:
            self.app.root.destroy()

    def test_play_chime_all_sound_types(self):
        """Verifies play_chime handles all procedural SoundTypes without throwing."""
        sound_names = ["GREETING", "JUMP", "BLUSH", "CELEBRATE", "STUDY_BELL", "CLICK"]
        for s_name in sound_names:
            with self.subTest(sound=s_name):
                # Should execute cleanly whether audio daemon is active or mocked
                self.app.play_chime(s_name)

    def test_actions_trigger_corresponding_sounds(self):
        """Tests that physical action animations call play_chime with specific sound signatures."""
        recorded_sounds = []
        original_play_chime = self.app.play_chime

        def mock_play(sound_type="GREETING"):
            recorded_sounds.append(sound_type)
            return original_play_chime(sound_type)

        self.app.play_chime = mock_play

        self.app.trigger_action("JUMPING")
        self.assertIn("JUMP", recorded_sounds)

        self.app.trigger_action("WAVING")
        self.assertIn("GREETING", recorded_sounds)

        self.app.trigger_action("BLUSHING")
        self.assertIn("BLUSH", recorded_sounds)

        self.app.trigger_action("CELEBRATING")
        self.assertIn("CELEBRATE", recorded_sounds)

    def test_scene_and_theme_trigger_click_sounds(self):
        """Tests that UI theme and scene selections trigger crisp click sound effects."""
        recorded_sounds = []
        self.app.play_chime = lambda s="CLICK": recorded_sounds.append(s)

        self.app.set_scene("Midnight Stars")
        self.assertIn("CLICK", recorded_sounds)

        self.app.set_theme("Midnight Violet")
        self.assertIn("CLICK", recorded_sounds)


if __name__ == "__main__":
    unittest.main()
