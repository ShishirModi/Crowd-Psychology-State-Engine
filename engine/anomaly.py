import numpy as np
from collections import deque

class AnomalyDetector:
    """
    Detects unusual events by comparing current crowd vectors against a historical window.
    """
    def __init__(self, history_size=100, z_threshold=2.5):
        self.history_size = history_size
        self.z_threshold = z_threshold
        # Store history of dynamic state vectors
        self.history = deque(maxlen=history_size)
        
    def train(self, historical_vectors):
        """Allows pre-loading history."""
        for v in historical_vectors:
            self.history.append(v)
            
    def update_and_detect(self, current_vector):
        """
        Updates history and checks if current_vector is anomalous.
        Returns: (is_anomaly: bool, anomaly_score: float)
        """
        # If not enough history, collect data but don't flag
        if len(self.history) < 20: 
            self.history.append(current_vector)
            return False, 0.0
            
        # Convert history to numpy array for stats [N_samples, M_features]
        hist_array = np.array(self.history)
        
        # Calculate Mean and Std Dev for each feature
        mean = np.mean(hist_array, axis=0)
        std = np.std(hist_array, axis=0)
        
        # Avoid division by zero
        std = np.where(std == 0, 1e-6, std)
        
        # Calculate Z-Score for the current vector
        # Z = |(X - Mean) / Std|
        z_scores = np.abs((current_vector - mean) / std)
        
        # Aggregate Z-Score (Mean Z represents overall system deviation)
        anomaly_score = np.max(z_scores)
        
        # Update history
        self.history.append(current_vector)
        
        is_anomaly = anomaly_score > self.z_threshold
        
        return is_anomaly, float(anomaly_score)
