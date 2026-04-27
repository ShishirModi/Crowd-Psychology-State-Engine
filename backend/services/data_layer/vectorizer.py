import numpy as np
import time
from datetime import datetime

class CrowdStateVectorizer:
    """
    Transforms raw signal data into structured vectors for analysis/ML models.
    Scales and normalizes inputs where appropriate.
    """
    def __init__(self):
        # Configuration for normalization (approximate max values)
        self.MAX_SPEED = 120.0 # km/h
        self.MAX_DENSITY = 1.0 # ratio
        
    def get_time_feature(self):
        """Returns normalized time of day (0.0 - 1.0)"""
        now = datetime.now()
        seconds_in_day = now.hour * 3600 + now.minute * 60 + now.second
        return seconds_in_day / 86400.0

    def create_state_vector(self, congestion_level, velocity_variance, gradient):
        """
        Creates the Dynamic Crowd State Vector.
        Structure: [density, flow_turbulence, pressure_gradient, time_factor]
        """
        # 1. Density (Congestion is already 0.0-1.0)
        density = np.clip(congestion_level, 0.0, 1.0)
        
        # 2. Turbulence (Velocity Variance - normalized arbitrarily)
        # Assuming variance > 5.0 is extreme
        turbulence = np.clip(velocity_variance / 5.0, 0.0, 1.0)
        
        # 3. Pressure/Compression Gradient
        # Gradient > 1.0 is very fast compression
        pressure = np.clip(gradient, -1.0, 1.0)
        
        # 4. Temporal factor
        time_factor = self.get_time_feature()
        
        vector = np.array([density, turbulence, pressure, time_factor], dtype=np.float32)
        return vector

    def create_environmental_vector(self, width_factor=1.0, weather_risk=0.0, event_risk=0.0):
        """
        Creates Hyper-Local Condition Vector.
        Structure: [passage_width_factor, weather_risk, event_indicator]
        Args:
            width_factor (float): 1.0 = Normal, 0.5 = Narrow, 0.1 = Bottleneck
            weather_risk (float): 0.0 = Clear, 1.0 = Extreme
            event_risk (float): 0.0 = None, 1.0 = Riot/Event
        """
        vector = np.array([width_factor, weather_risk, event_risk], dtype=np.float32)
        return vector
