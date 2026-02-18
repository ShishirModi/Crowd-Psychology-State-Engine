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
        Returns: (gradient_value, fit_quality)
        fit_quality is 0.0 to 1.0 (R-squared approximation)
        """
        if len(self.congestion_history) < 2:
            return 0.0, 0.5 # Neutral quality for insufficient data
            
        data = np.array(self.congestion_history)
        current_level = data[-1]
        
        # Default quality
        fit_quality = 0.5
        slope = 0.0
        
        if len(data) >= 5:
            x = np.arange(len(data))
            # Polyfit basic linear regression
            slope, residuals, rank, singular_values, rcond = np.polyfit(x, data, 1, full=True)
            
            # Calculate R-squared manually if residuals are present
            if len(residuals) > 0:
                ss_res = residuals[0]
                ss_tot = np.sum((data - np.mean(data))**2)
                
                if ss_tot > 1e-6: # Avoid divide by zero for flat line
                    r_squared = 1 - (ss_res / ss_tot)
                    fit_quality = max(0.0, min(1.0, r_squared))
                else:
                    fit_quality = 1.0 # Perfect fit (flat line)
            else:
                 fit_quality = 1.0 # Perfect fit
                 
            slope = slope[0] # Polyfit returns [slope, intercept]
        else:
            slope = data[-1] - data[-2]
            fit_quality = 0.5 # Too few points for reliable R2
            
        w_level = 0.6
        w_slope = 0.4
        
        metric = (w_level * current_level) + (w_slope * slope * 5)
        return max(0.0, min(1.0, metric)), fit_quality

    def compute_velocity_variance(self):
        """
        Computes variance in speed over the history window.
        High variance = stop-and-go waves (Turbulence).
        """
        if len(self.speed_history) < 3:
            return 0.0
            
        speeds = np.array(self.speed_history)
        mean_speed = np.mean(speeds)
        std_dev = np.std(speeds)
        
        if mean_speed < 1.0:
            # If speed is near zero, variance is less meaningful (stopped traffic)
            # Return raw std dev as a fallback or 0 if truly stopped
            return float(std_dev)
            
        # Coefficient of Variation (CV) = Sigma / Mu
        # normalized to be somewhat comparable to previous logic (0-2 range roughly)
        # CV of 0.2 (20% fluctation) is high. 
        # Let's return raw CV for now, classifier will handle scaling.
        cv = std_dev / mean_speed
        
        return float(cv)
