import unittest
from metrics.compression import CrowdMetrics


class TestCrowdMetrics(unittest.TestCase):
    def setUp(self):
        self.metrics = CrowdMetrics(history_size=5)

    def test_initial_state(self):
        grad, quality, details = self.metrics.compute_compression_gradient()
        self.assertEqual(grad, 0.0)
        self.assertEqual(details["method"], "insufficient_data")

        cv, vv_details = self.metrics.compute_velocity_variance()
        self.assertEqual(cv, 0.0)
        self.assertEqual(vv_details["method"], "insufficient_data")

    def test_gradient_computation(self):
        for i in range(5):
            self.metrics.update(congestion_level=i * 0.1)

        grad, quality, details = self.metrics.compute_compression_gradient()
        self.assertGreater(grad, 0.0)
        self.assertIn("trend", details)
        self.assertEqual(details["trend"], "Rising")

    def test_gradient_details_complete(self):
        for i in range(5):
            self.metrics.update(congestion_level=0.5)

        _, _, details = self.metrics.compute_compression_gradient()
        for key in ("current_level", "slope", "fit_quality_r2", "method", "verdict"):
            self.assertIn(key, details)

    def test_velocity_variance_steady(self):
        for _ in range(5):
            self.metrics.update(congestion_level=0.5, current_speed=50.0)
        cv, details = self.metrics.compute_velocity_variance()
        self.assertEqual(cv, 0.0)
        self.assertEqual(details["turbulence_level"], "Negligible")

    def test_velocity_variance_fluctuating(self):
        for _ in range(3):
            self.metrics.update(congestion_level=0.5, current_speed=50.0)
        self.metrics.update(congestion_level=0.5, current_speed=100.0)
        self.metrics.update(congestion_level=0.5, current_speed=10.0)

        cv, details = self.metrics.compute_velocity_variance()
        self.assertGreater(cv, 0.0)
        self.assertIn("turbulence_level", details)


if __name__ == "__main__":
    unittest.main()
