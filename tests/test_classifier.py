import unittest
from engine.classifier import CrowdClassifier

class TestCrowdClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = CrowdClassifier()

    def test_stable_state(self):
        # Low gradient -> Stable
        state, conf = self.classifier.classify(compression_gradient=0.05)
        self.assertEqual(state, "Stable")
        self.assertGreater(conf, 0.9)

    def test_compressing_state(self):
        # Medium gradient -> Compressing
        # Thresholds: stable=0.1, compressing=0.5
        state, conf = self.classifier.classify(compression_gradient=0.45)
        self.assertIn("Compressing", state)

    def test_volatile_state(self):
        # High gradient -> Volatile
        state, conf = self.classifier.classify(compression_gradient=0.9)
        self.assertEqual(state, "Volatile")

    def test_anomaly_flag(self):
        # Anomaly score > 2.5 should append "(Unusual Event)"
        state, conf = self.classifier.classify(compression_gradient=0.05, anomaly_score=3.0)
        self.assertIn("(Unusual Event)", state)
        self.assertEqual(conf, 0.5)

if __name__ == '__main__':
    unittest.main()
