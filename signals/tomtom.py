import requests
import random
import time
import os
from utils.config_loader import get_config

class TomTomSignal:
    def __init__(self):
        self.config = get_config()
        self.tomtom_config = self.config.get('api', {}).get('tomtom', {})
        
        self.api_key = None
        if self.tomtom_config.get('use_env_key'):
            env_var = self.tomtom_config.get('env_key_name')
            if env_var:
                self.api_key = os.getenv(env_var)
                if self.api_key:
                    print(f"DEBUG: Using API Key from Environment Variable: {env_var}")
                else:
                    print(f"WARNING: Environment Variable {env_var} not set or empty.")
            else:
                 print("WARNING: 'env_key_name' not found in config for TomTom.")
        
        # Fallback to direct key if not in env
        if not self.api_key:
             self.api_key = self.tomtom_config.get('key')

        self.base_url = self.tomtom_config.get('base_url')
        self.simulation_enabled = self.config.get('simulation', {}).get('enabled', True)
        self.location = self.config.get('location', {})
        
    def set_location(self, lat, lon, name="Unknown"):
        """Updates the monitored location dynamically."""
        self.location['lat'] = lat
        self.location['lon'] = lon
        self.location['name'] = name
        print(f"Signal: Location updated to {name} ({lat}, {lon})")
        
    def fetch_telemetry(self):
        """
        Fetches full telemetry: Congestion, Speed, FreeFlow.
        Returns dict.
        """
        if not self.api_key:
            if self.simulation_enabled:
                return self._simulate_telemetry()
            else:
                print("Error: No API key and simulation disabled.")
                return None
        
        try:
            # Request flow data for the specific point
            # TomTom Flow Segment Data returns data for the segment closest to the given coordinates
            # Format: https://{baseUrl}/traffic/services/4/flowSegmentData/absolute/10/json?key={apiKey}&point={point}
            
            # Format coordinates to 5 decimal places (TomTom best practice)
            lat = round(self.location.get('lat'), 5)
            lon = round(self.location.get('lon'), 5)
            point = f"{lat},{lon}"
            
            # Construct URL manually or use params. TomTom documentation specifies structure.
            # Using '10' as zoom level (approx city level)
            url = f"{self.base_url}/absolute/10/json"
            
            params = {
                'key': self.api_key,
                'point': point,
                'unit': 'KMPH',
                'cb': int(time.time()) # Cache buster
            }
            
            print(f"DEBUG: Requesting TomTom API for {point}... (TS: {params['cb']})")
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 403:
                print("Error: API Key Invalid or Forbidden.")
                return self._simulate_telemetry()
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            if 'flowSegmentData' not in data:
                print(f"Warning: 'flowSegmentData' missing in response. Data keys: {list(data.keys())}")
                return self._simulate_telemetry()
                
            flow_data = data['flowSegmentData']
            current_speed = flow_data.get('currentSpeed')
            free_flow_speed = flow_data.get('freeFlowSpeed')
            
            if current_speed is None or free_flow_speed is None:
                print("Warning: Missing speed data in response.")
                return self._simulate_telemetry()
                
            # Sanity Check for zero free-flow
            if free_flow_speed <= 0:
                free_flow_speed = 50.0 # Default fallback
                
            # Calculate congestion
            congestion = 0.0
            if free_flow_speed > 0:
                congestion = 1.0 - (current_speed / free_flow_speed)
                congestion = max(0.0, min(1.0, congestion))
            
            return {
                "congestion": congestion,
                "current_speed": current_speed,
                "free_flow_speed": free_flow_speed,
                "is_simulated": False
            }
            
        except Exception as e:
            from utils.security import scrub_sensitive_data
            error_msg = scrub_sensitive_data(e)
            print(f"API Error: {error_msg}. Falling back to simulation.")
            return self._simulate_telemetry()

    def _simulate_telemetry(self):
        """Simulates detailed telemetry."""
        # Bias towards moderate congestion (0.3 - 0.7)
        base = 0.5
        noise = random.uniform(-0.2, 0.3)
        congestion = max(0.0, min(1.0, base + noise))
        
        # Mock speeds (assuming 50km/h free flow)
        free_flow = 50.0
        current = free_flow * (1.0 - congestion)
        
        return {
            "congestion": congestion,
            "current_speed": current,
            "free_flow_speed": free_flow,
            "is_simulated": True
        }

# Singleton or factory if needed
def get_signal_provider():
    return TomTomSignal()
