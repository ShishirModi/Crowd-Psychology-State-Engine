import requests
import os
import time
from utils.config_loader import get_config


def _fetch_weather_risk_live(lat: float, lon: float, api_key: str, base_url: str):
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        weather_id = data['weather'][0]['id']
        description = data['weather'][0]['main']
        risk = 0.0
        if 200 <= weather_id < 300:
            risk = 1.0
        elif 300 <= weather_id < 400:
            risk = 0.3
        elif 500 <= weather_id < 600:
            risk = 0.5 if weather_id in (500, 501) else 0.8
        elif 600 <= weather_id < 700:
            risk = 0.7
        elif 700 <= weather_id < 800:
            risk = 1.0 if weather_id == 781 else (0.9 if weather_id == 771 else 0.4)
        elif weather_id == 800:
            risk = 0.0
        elif 800 < weather_id < 900:
            risk = 0.1
        return risk, description, data
    except Exception as e:
        print(f"Weather API Error: {e}")
        return None, "Error", {}


class OpenWeatherMapSignal:
    # Class-level in-memory cache: {key: {'ts': float, 'result': tuple}}
    _cache: dict = {}
    _cache_ttl = 600  # 10 minutes — mirrors old @st.cache_data(ttl=600)

    def __init__(self):
        config = get_config()
        weather_config = config.get('api', {}).get('openweathermap', {})
        env_var = weather_config.get('env_key_name', 'OPENWEATHERMAP_API_KEY')
        self.api_key = os.getenv(env_var)
        self.base_url = weather_config.get(
            'base_url', 'https://api.openweathermap.org/data/2.5/weather'
        )

    def fetch_weather_risk(self, lat: float, lon: float):
        if not self.api_key:
            return None, "No API Key", {}
        key = f"{lat:.4f},{lon:.4f}"
        entry = OpenWeatherMapSignal._cache.get(key)
        if entry and time.monotonic() - entry['ts'] < self._cache_ttl:
            return entry['result']
        result = _fetch_weather_risk_live(lat, lon, self.api_key, self.base_url)
        OpenWeatherMapSignal._cache[key] = {'ts': time.monotonic(), 'result': result}
        return result
