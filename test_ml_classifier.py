#!/usr/bin/env python3
"""
test_ml_classifier.py — Unit Tests for ML Emotion & Intent Classifier & Dialogue Engine Integration
"""

import os
import shutil
import tempfile
import unittest

from companion_db import (
    clear_db,
    get_dataset_stats,
    get_model_runs,
    get_training_data,
    init_db,
)
from dialogue_engine import DialogueEngine, Emotion, respond
from ml_classifier import MLClassifier, build_feature_extractor, get_classifier


class TestMLFeatureExtraction(unittest.TestCase):
    """Tests TF-IDF feature extraction pipeline combining word and char n-grams."""

    def test_feature_extractor_build_and_transform(self):
        extractor = build_feature_extractor()
        corpus = [
            "Hello Mia, good morning!",
            "I love you so much sweetheart! ♥",
            "Tell me a funny joke haha!",
        ]
        matrix = extractor.fit_transform(corpus)
        self.assertEqual(matrix.shape[0], 3)
        self.assertGreater(matrix.shape[1], 10)


class TestMLTrainingAndEvaluation(unittest.TestCase):
    """Tests scikit-learn training pipeline, metrics evaluation, and model run logging."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ml.db")
        self.model_path = os.path.join(self.temp_dir, "test_model.pkl")
        init_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_train_pipeline_and_metrics(self):
        clf = MLClassifier(model_path=self.model_path)
        metrics = clf.train(db_path=self.db_path, log_run=True, save_model=True)

        self.assertTrue(clf.is_trained)
        self.assertGreaterEqual(metrics["samples_count"], 150)
        self.assertGreaterEqual(metrics["emotion_accuracy"], 0.80)
        self.assertGreaterEqual(metrics["intent_accuracy"], 0.80)
        self.assertGreaterEqual(metrics["overall_accuracy"], 0.80)
        self.assertTrue(os.path.exists(self.model_path))

        # Verify run logged in model_runs table
        runs = get_model_runs(limit=5, db_path=self.db_path)
        self.assertGreaterEqual(len(runs), 1)
        latest = runs[0]
        self.assertEqual(latest["model_name"], "tfidf_logreg_companion")
        self.assertAlmostEqual(latest["accuracy"], metrics["overall_accuracy"], places=4)


class TestMLPredictionAndConfidence(unittest.TestCase):
    """Tests emotion and intent predictions, calibrated confidence scoring, and probabilities."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_eval.db")
        cls.model_path = os.path.join(cls.temp_dir, "eval_model.pkl")
        init_db(cls.db_path)
        cls.clf = MLClassifier(model_path=cls.model_path)
        cls.clf.train(db_path=cls.db_path, log_run=False, save_model=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_predict_emotion_and_intent_structure(self):
        res = self.clf.predict("Good morning Mia! You are so cute! 💕")
        self.assertIn("text", res)
        self.assertIn("emotion", res)
        self.assertIn("emotion_confidence", res)
        self.assertIn("intent", res)
        self.assertIn("intent_confidence", res)
        self.assertIn("all_emotion_probs", res)
        self.assertIn("all_intent_probs", res)
        self.assertEqual(res["method"], "ml")

        self.assertGreater(res["emotion_confidence"], 0.0)
        self.assertLessEqual(res["emotion_confidence"], 1.0)
        self.assertGreater(res["intent_confidence"], 0.0)
        self.assertLessEqual(res["intent_confidence"], 1.0)

        # Probabilities should sum to approximately 1.0
        emo_sum = sum(res["all_emotion_probs"].values())
        int_sum = sum(res["all_intent_probs"].values())
        self.assertAlmostEqual(emo_sum, 1.0, places=2)
        self.assertAlmostEqual(int_sum, 1.0, places=2)

    def test_predict_specific_emotions(self):
        samples = [
            ("I love you so much my darling! ♥", "LOVE"),
            ("Tell me a funny joke haha, that was hilarious lol!", "PLAYFUL"),
            ("I'm feeling so shy and flustered... *blushes*", "SHY"),
            ("Yay, today was fantastic and wonderful! Great job!", "HAPPY"),
        ]
        for text, expected_emo in samples:
            with self.subTest(text=text, expected=expected_emo):
                res = self.clf.predict(text)
                self.assertEqual(res["emotion"], expected_emo)

    def test_predict_specific_intents(self):
        samples = [
            ("Hello Mia, good morning to you!", "GREETING"),
            ("Goodbye, sweet dreams and sleep well!", "FAREWELL"),
            ("You are truly gorgeous, stunning and wonderful!", "COMPLIMENT"),
            ("What is your favorite color and hobby?", "QUESTION"),
        ]
        for text, expected_intent in samples:
            with self.subTest(text=text, expected=expected_intent):
                res = self.clf.predict(text)
                self.assertEqual(res["intent"], expected_intent)


class TestMLPersistence(unittest.TestCase):
    """Tests model serialization and loading from disk."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_persist.db")
        self.model_path = os.path.join(self.temp_dir, "persist_model.pkl")
        init_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_model(self):
        clf1 = MLClassifier(model_path=self.model_path)
        clf1.train(db_path=self.db_path, log_run=False, save_model=True)
        pred1 = clf1.predict("Let's dance and play a fun game haha!")

        # Load into new instance
        clf2 = MLClassifier(model_path=self.model_path)
        self.assertFalse(clf2.is_trained)
        loaded = clf2.load()
        self.assertTrue(loaded)
        self.assertTrue(clf2.is_trained)

        pred2 = clf2.predict("Let's dance and play a fun game haha!")
        self.assertEqual(pred1["emotion"], pred2["emotion"])
        self.assertEqual(pred1["intent"], pred2["intent"])
        self.assertAlmostEqual(pred1["emotion_confidence"], pred2["emotion_confidence"], places=4)


class TestMLFallbackBehavior(unittest.TestCase):
    """Tests heuristic fallback when inputs are empty or model is untrained."""

    def test_empty_string_prediction(self):
        clf = MLClassifier(model_path="/nonexistent/model.pkl")
        res = clf.predict("")
        self.assertEqual(res["emotion"], "NORMAL")
        self.assertEqual(res["intent"], "CHAT")
        self.assertEqual(res["method"], "heuristic")

    def test_heuristic_predict_fallback(self):
        clf = MLClassifier(model_path="/nonexistent/model.pkl")
        res = clf._heuristic_predict("Hello, how are you today?")
        self.assertEqual(res["intent"], "GREETING")
        self.assertEqual(res["method"], "heuristic")


class TestDialogueEngineMLIntegration(unittest.TestCase):
    """Tests DialogueEngine seamless integration with MLClassifier."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "dialogue_ml.db")
        self.model_path = os.path.join(self.temp_dir, "dialogue_model.pkl")
        init_db(self.db_path)

        # Train and prepare classifier
        self.clf = MLClassifier(model_path=self.model_path)
        self.clf.train(db_path=self.db_path, log_run=False, save_model=True)
        self.engine = DialogueEngine(db_path=self.db_path, classifier=self.clf)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_process_message_with_ml_enrichment(self):
        res = self.engine.process_message("Good morning Mia! You are so sweet and cute! 💕")

        self.assertIn("user_text", res)
        self.assertIn("reply_text", res)
        self.assertIn("emotion", res)
        self.assertIn("emotion_confidence", res)
        self.assertIn("intent", res)
        self.assertIn("intent_confidence", res)
        self.assertIn("method", res)
        self.assertIn("friendship_level", res)
        self.assertIn("greeting_count", res)

        self.assertTrue(0.0 <= res["emotion_confidence"] <= 1.0)
        self.assertTrue(0.0 <= res["intent_confidence"] <= 1.0)
        self.assertIn(res["method"], ("ml", "heuristic"))
        self.assertEqual(res["intent"], "GREETING")

    def test_convenience_respond_with_engine(self):
        res = respond("Tell me a funny joke haha!", db_path=self.db_path)
        self.assertIn("emotion_confidence", res)
        self.assertIn("intent", res)
        self.assertEqual(res["emotion"], "PLAYFUL")


if __name__ == "__main__":
    unittest.main()
