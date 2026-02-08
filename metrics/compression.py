import numpy as np
from collections import deque

class CrowdMetrics:
    def __init__(self, history_size=12):
        # Assuming 5-second intervals, 12 samples = 60 seconds history
        self.congestion_history = deque(maxlen=history_size)
        self.speed_history = deque(maxlen=history_size)
    
    def update(self, congestion_level, current_speed=None):
        """
        Updates the history with new telemetry.
        """
        if congestion_level is not None:
            self.congestion_history.append(congestion_level)
        if current_speed is not None:
            self.speed_history.append(current_speed)
            
    def compute_compression_gradient(self):
        """
        Computes the compression gradient based on congestion history.
        """
        if len(self.congestion_history) < 2:
            return 0.0
            
        data = np.array(self.congestion_history)
        current_level = data[-1]
        delta = data[-1] - data[-2]
        
        if len(data) >= 5:
            x = np.arange(len(data))
            slope, _ = np.polyfit(x, data, 1)
        else:
            slope = delta
            
        w_level = 0.6
        w_slope = 0.4
        metric = (w_level * current_level) + (w_slope * max(0.0, slope * 5))
        return max(0.0, min(1.0, metric))

    def compute_velocity_variance(self):
        """
        Computes variance in speed over the history window.
        High variance = stop-and-go waves (Turbulence).
        """
        if len(self.speed_history) < 3:
            return 0.0
            
        # Standard Deviation / Mean to look at Coefficient of Variation
        # But simple Variance is requested.
        # Let's normalize it slightly so it doesn't explode.
        
        speeds = np.array(self.speed_history)
        variance = np.var(speeds)
        
        # Normalize? 
        # If variance is 100 (e.g. speed jumps 40 <-> 60), that is high.
        # If variance is 0, steady flow.
        return float(variance)
