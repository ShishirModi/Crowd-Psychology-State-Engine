import unittest
from metrics.compression import CrowdMetrics

class TestCrowdMetrics(unittest.TestCase):
    def setUp(self):
        self.metrics = CrowdMetrics(history_size=5)

    def test_initial_state(self):
        self.assertEqual(self.metrics.compute_compression_gradient(), 0.0)
        self.assertEqual(self.metrics.compute_velocity_variance(), 0.0)

    def test_gradient_computation(self):
        # Linear increase
        for i in range(5):
            self.metrics.update(congestion_level=i*0.1) # 0.0, 0.1, 0.2...
        
        grad = self.metrics.compute_compression_gradient()
        self.assertGreater(grad, 0.0, "Gradient should be positive for increasing congestion")

    def test_velocity_variance(self):
        # Perfect steady speed -> 0 variance
        for _ in range(5):
            self.metrics.update(congestion_level=0.5, current_speed=50.0)
        self.assertEqual(self.metrics.compute_velocity_variance(), 0.0)

        # Fluctuating speed
        self.metrics.update(congestion_level=0.5, current_speed=100.0)
        self.metrics.update(congestion_level=0.5, current_speed=0.0)
        
        var = self.metrics.compute_velocity_variance()
        self.assertGreater(var, 0.0, "Variance should be positive for fluctuating speed")

if __name__ == '__main__':
    unittest.main()
