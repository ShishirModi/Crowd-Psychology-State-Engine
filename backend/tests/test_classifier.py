import unittest
from services.engine.classifier import CrowdClassifier


class TestCrowdClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = CrowdClassifier()

    def test_stable_state(self):
        state, conf, bd = self.classifier.classify(compression_gradient=0.05)
        self.assertEqual(state, "Stable")
        self.assertGreater(conf, 0.5)  # may have penalties from defaults

    def test_compressing_state(self):
        state, conf, bd = self.classifier.classify(
            compression_gradient=0.6, history_len=10, gradient_quality=0.9
        )
        self.assertEqual(state, "Compressing")
        self.assertIn("compression_gradient", bd)

    def test_volatile_state(self):
        state, conf, bd = self.classifier.classify(
            compression_gradient=0.9, history_len=10, gradient_quality=0.9
        )
        self.assertEqual(state, "Volatile")

    def test_agitated_state(self):
        state, conf, bd = self.classifier.classify(
            compression_gradient=0.96, history_len=10, gradient_quality=0.9
        )
        self.assertEqual(state, "Agitated")

    def test_anomaly_flag(self):
        state, conf, bd = self.classifier.classify(
            compression_gradient=0.05, anomaly_score=3.0
        )
        self.assertIn("Anomaly Detected", state)

    def test_velocity_override(self):
        # Compressing + high turbulence → Volatile
        state, conf, bd = self.classifier.classify(
            compression_gradient=0.6, velocity_variance=0.3,
            history_len=10, gradient_quality=0.9,
        )
        self.assertEqual(state, "Volatile")

    def test_breakdown_has_risk_score(self):
        _, _, bd = self.classifier.classify(compression_gradient=0.5)
        self.assertIn("risk_score", bd)
        self.assertIsInstance(bd["risk_score"]["value"], float)

    def test_breakdown_has_confidence(self):
        _, _, bd = self.classifier.classify(compression_gradient=0.5)
        self.assertIn("confidence", bd)
        self.assertIn("penalties", bd["confidence"])
        self.assertIn("bonuses", bd["confidence"])


if __name__ == "__main__":
    unittest.main()
