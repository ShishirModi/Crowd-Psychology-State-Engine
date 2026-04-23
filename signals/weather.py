import requests
import os
import streamlit as st
from utils.config_loader import get_config

@st.cache_data(ttl=600)
def _cached_fetch_weather_risk(lat, lon, api_key, base_url):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }

    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Map weather conditions to risk (Source: https://openweathermap.org/weather-conditions)
        weather_id = data['weather'][0]['id']
        description = data['weather'][0]['main']

        risk = 0.0

        # Thunderstorm (Group 2xx)
        if 200 <= weather_id < 300:
            risk = 1.0
        # Drizzle (Group 3xx)
        elif 300 <= weather_id < 400:
            risk = 0.3
        # Rain (Group 5xx)
        elif 500 <= weather_id < 600:
            if weather_id in [500, 501]: # Light/Mod rain
                risk = 0.5
            else: # Heavy rain
                risk = 0.8
        # Snow (Group 6xx)
        elif 600 <= weather_id < 700:
            risk = 0.7
        # Atmosphere (Group 7xx: Fog, Ash, Squall)
        elif 700 <= weather_id < 800:
            if weather_id == 781: # Tornado
                risk = 1.0
            elif weather_id == 771: # Squall
                risk = 0.9
            else:
                risk = 0.4 # Fog/Mist
        # Clear (Group 800)
        elif weather_id == 800:
            risk = 0.0
        # Clouds (Group 80x)
        elif 800 < weather_id < 900:
            risk = 0.1

        return risk, description, data

    except Exception as e:
        print(f"Weather API Error: {e}")
        return None, "Error", {}


class OpenWeatherMapSignal:
    def __init__(self):
        self.config = get_config()
        self.weather_config = self.config.get('api', {}).get('openweathermap', {})
        
        self.api_key = None
        if self.weather_config.get('use_env_key', True):
            # Default to OPENWEATHERMAP_API_KEY if config is missing but class is instantiated
            env_var = self.weather_config.get('env_key_name', 'OPENWEATHERMAP_API_KEY')
            self.api_key = os.getenv(env_var)
            
        self.base_url = self.weather_config.get('base_url', "https://api.openweathermap.org/data/2.5/weather")

    def fetch_weather_risk(self, lat, lon):
        """
        Fetches current weather and maps it to a risk factor (0.0 to 1.0).
        Returns: (risk_float, condition_string, raw_data_dict)
        """
        if not self.api_key:
            return None, "No API Key", {}

        return _cached_fetch_weather_risk(lat, lon, self.api_key, self.base_url)
