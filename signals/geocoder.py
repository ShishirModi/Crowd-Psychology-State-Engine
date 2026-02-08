import requests
import os
from utils.config_loader import get_config

class TomTomGeocoder:
    def __init__(self):
        self.config = get_config()
        self.tomtom_config = self.config.get('api', {}).get('tomtom', {})
        
        # Resolve API Key reuse
        self.api_key = None
        if self.tomtom_config.get('use_env_key'):
             env_var = self.tomtom_config.get('env_key_name')
             if env_var:
                 self.api_key = os.getenv(env_var)
        
        if not self.api_key:
             self.api_key = self.tomtom_config.get('key')
             
        self.search_url = self.tomtom_config.get('search_url', "https://api.tomtom.com/search/2/search")

    def search(self, query):
        """
        Search for a location string. Returns a list of dicts with name, lat, lon.
        """
        if not self.api_key:
            print("Error: API Key missing for Geocoding.")
            return []
            
        try:
            url = f"{self.search_url}/{query}.json"
            params = {
                'key': self.api_key,
                'limit': 5, # Show top 5 results
                'typeahead': 'true'
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get('results', []):
                address = result.get('address', {}).get('freeformAddress', 'Unknown Address')
                position = result.get('position', {})
                results.append({
                    'name': address,
                    'lat': position.get('lat'),
                    'lon': position.get('lon')
                })
                
            return results
            
        except Exception as e:
            from utils.security import scrub_sensitive_data
            print(f"Geocoding Error: {scrub_sensitive_data(e)}")
            return []

    def get_location_interactive(self):
        """
        Loops until user selects a valid location. Returns dict {lat, lon}.
        """
        while True:
            print("\n" + "="*40)
            query = input("Enter location to monitor (or 'exit'): ").strip()
            if query.lower() == 'exit':
                return None
                
            if not query:
                continue
                
            print(f"Searching for '{query}'...")
            candidates = self.search(query)
            
            if not candidates:
                print("❌ Location not found. Please try again.")
                continue
                
            if not candidates:
                print("❌ Location not found. Please try again.")
                continue
            
            print(f"\nFound {len(candidates)} matches:")
            for idx, cand in enumerate(candidates):
                print(f"  [{idx+1}] {cand['name']} ({cand['lat']}, {cand['lon']})")
                
            print("  [0] Search again")
            
            choice = input("\nSelect a location [1-5] or 0 to retry: ").strip()
            
            if choice == '0':
                continue
                
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(candidates):
                    selected = candidates[choice_idx]
                    print(f"✅ Selected: {selected['name']}")
                    return selected
                else:
                    print("❌ Invalid selection.")
            except ValueError:
                print("❌ Invalid input.")
