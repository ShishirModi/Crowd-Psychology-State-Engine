from utils.config_loader import get_config

class CrowdClassifier:
    def __init__(self):
        self.config = get_config()
        self.thresholds = self.config.get('thresholds', {}).get('compression_gradient', {})
        
        # Defaults if config missing
        self.t_compressing = self.thresholds.get('compressing', 0.5)
        self.t_volatile = self.thresholds.get('volatile', 0.8)
        self.t_stable = self.thresholds.get('stable', 0.1)

    def classify(self, compression_gradient, velocity_variance=0, anomaly_score=0.0, is_simulated=False, history_len=10, gradient_quality=0.5):
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
        base_confidence = 1.0
        
        # 1. Determine State based on Compression Gradient
        if compression_gradient < self.t_stable:
            state = "Stable"
            # High confidence if far below threshold
            base_confidence = 0.95
            
        elif compression_gradient < self.t_compressing:
            # Transition zone (Stable -> Compressing)
            state = "Stable"
            # Lower confidence as we approach the limit
            dist = self.t_compressing - compression_gradient
            range_val = self.t_compressing - self.t_stable
            base_confidence = 0.8 + (dist / range_val) * 0.1
                 
        elif compression_gradient < self.t_volatile:
            state = "Compressing"
            # Transition zone (Compressing -> Volatile)
            # Confidence creates a "hump" - lower near boundaries, higher in center
            midpoint = (self.t_compressing + self.t_volatile) / 2
            dist_norm = abs(compression_gradient - midpoint) / ((self.t_volatile - self.t_compressing) / 2)
            base_confidence = 0.9 - (dist_norm * 0.2) # 0.9 at center, 0.7 at edges
            
        else:
            state = "Volatile"
            base_confidence = 0.9
            if compression_gradient > 0.95:
                state = "Agitated"
                base_confidence = 0.95
        
        # 2. Velocity Variance (Coefficient of Variation) Override
        # CV > 0.25 (25% fluctuation) implies significant turbulence
        if velocity_variance > 0.25:
            if state == "Compressing":
                state = "Volatile" # Upgrade severity due to turbulence
                base_confidence = 0.8
            elif state == "Volatile":
                state = "Agitated"
                base_confidence = 0.85
            else:
                # Stable but turbulent? Unusual.
                base_confidence -= 0.1
            
        # 3. Anomaly Override
        if anomaly_score > 2.5: # Z-Score threshold
            if state in ["Stable", "Compressing"]:
                 state += " (Unusual Event)"
                 base_confidence -= 0.15 # Lower confidence due to unexplained anomaly
            
        # 4. Apply Penalties & Bonuses
        final_confidence = base_confidence
        
        # Shape: Simulation Penalty
        if is_simulated:
            final_confidence -= 0.2
            
        # Shape: Warmup Penalty
        if history_len < 5:
            final_confidence -= 0.3
            
        # Shape: Gradient Quality (Goodness of Fit)
        if gradient_quality < 0.8:
            # Noisy trend -> Reduce confidence
            final_confidence -= 0.15
        elif gradient_quality > 0.95:
            # Very strong trend -> Slight boost
            final_confidence += 0.05
            
        return state, max(0.1, min(1.0, round(final_confidence, 2)))
