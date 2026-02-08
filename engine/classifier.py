from utils.config_loader import get_config

class CrowdClassifier:
    def __init__(self):
        self.config = get_config()
        self.thresholds = self.config.get('thresholds', {}).get('compression_gradient', {})
        
        # Defaults if config missing
        self.t_compressing = self.thresholds.get('compressing', 0.5)
        self.t_volatile = self.thresholds.get('volatile', 0.8)
        self.t_stable = self.thresholds.get('stable', 0.1)

    def classify(self, compression_gradient, velocity_variance=0, anomaly_score=0.0):
        """
        Classifies the crowd state based on metrics.
        Returns (state_string, confidence_float)
        """
        # Logic:
        # Low compression -> Stable
        # Med compression -> Compressing
        # High compression -> Volatile
        # High compression + variance -> Agitated
        
        state = "Stable"
        confidence = 0.9 # Default high confidence for base state
        
        if compression_gradient < self.t_stable:
            state = "Stable"
            confidence = 0.95
            
        elif compression_gradient < self.t_compressing:
            # Transition zone
            state = "Stable" # Still considered stable but monitoring
            if compression_gradient > (self.t_compressing * 0.8):
                 state = "Compressing" # Early warning
                 confidence = 0.6
            else:
                 confidence = 0.8 - (compression_gradient * 0.5)
                 
        elif compression_gradient < self.t_volatile:
            state = "Compressing"
            # Confidence increases as we move away from the boundary
            confidence = 0.7 + ((compression_gradient - self.t_compressing) / (self.t_volatile - self.t_compressing)) * 0.2
            
        else:
            state = "Volatile"
            confidence = 0.85
            if compression_gradient > 0.95:
                state = "Agitated"
                confidence = 0.9
        
        # Simple override for fragmenting (mock logic)
        if velocity_variance > 2.0:
            state = "Fragmenting"
            confidence = 0.7
            
        # Anomaly Override / Modifier
        if anomaly_score > 2.5: # Z-Score threshold
            # If already critical, just Note it. If stable, flag it.
            if state in ["Stable", "Compressing"]:
                 state += " (Unusual Event)"
                 confidence = 0.5 # Lower confidence due to unexplained anomaly
            
        return state, round(confidence, 2)
