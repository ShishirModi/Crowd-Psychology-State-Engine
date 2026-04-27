import unittest
import numpy as np
from services.data_layer.vectorizer import CrowdStateVectorizer

class TestVectorizer(unittest.TestCase):
    def setUp(self):
        self.vectorizer = CrowdStateVectorizer()

    def test_state_vector_shape(self):
        vector = self.vectorizer.create_state_vector(congestion_level=0.5, velocity_variance=0.1, gradient=0.05)
        self.assertEqual(vector.shape, (4,), "State vector should have 4 dimensions")
        self.assertEqual(vector[0], 0.5, "First element should be density/congestion")

    def test_environmental_vector(self):
        vector = self.vectorizer.create_environmental_vector(width_factor=0.5, weather_risk=1.0, event_risk=0.0)
        self.assertEqual(vector.shape, (3,), "Env vector should have 3 dimensions")
        self.assertEqual(vector[0], 0.5)
        self.assertEqual(vector[1], 1.0)

if __name__ == '__main__':
    unittest.main()
