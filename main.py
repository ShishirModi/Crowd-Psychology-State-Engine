import sys
import time
from signals.tomtom import get_signal_provider
from metrics.compression import CrowdMetrics
from engine.classifier import CrowdClassifier
from interventions.recommender import InterventionRecommender
from utils.config_loader import load_config
from utils.time_helper import get_local_time

from signals.geocoder import TomTomGeocoder

def main():
    print("Crowd Psychology State Engine (CPSE) - Initializing...")
    config = load_config()
    
    # Initialize implementation
    try:
        signal_provider = get_signal_provider()
        geocoder = TomTomGeocoder()
        metrics = CrowdMetrics()
        classifier = CrowdClassifier()
        recommender = InterventionRecommender()
    except Exception as e:
        print(f"Initialization Failed: {e}")
        return

    # Interactive Location Selection
    if config.get('api', {}).get('tomtom', {}).get('key') or config.get('api', {}).get('tomtom', {}).get('use_env_key'):
        # Ask user if they want to choose a location
        print("\nConfigured Location: " + str(config.get('location', {}).get('name', 'Unknown')))
        change = input("Do you want to search for a different location? (y/n): ").strip().lower()
        if change == 'y':
            selected = geocoder.get_location_interactive()
            if selected:
                 signal_provider.set_location(selected['lat'], selected['lon'], selected['name'])
                 print(f"Monitoring switched to: {selected['name']}")
    
    print("System Online. Monitoring Signals...")
    print("-" * 50)

    try:
        while True:
            # 1. Fetch Signal
            congestion = signal_provider.fetch_congestion()
            
            if congestion is None:
                print("No signal received. Sleeping...")
                time.sleep(2)
                continue
                
            # 2. Update Metrics
            metrics.update(congestion)
            compression_gradient = metrics.compute_compression_gradient()
            velocity_variance = metrics.compute_velocity_variance()
            
            # 3. Classify State
            state, confidence = classifier.classify(compression_gradient, velocity_variance)
            
            # 4. Get Recommendations
            actions = recommender.get_recommendations(state)
            
            # 5. Output
            loc = signal_provider.location
            local_time = get_local_time(loc.get('lat', 0), loc.get('lon', 0))
            
            # Clear screen ANSI code
            print("\033[2J\033[H", end="") 
            print("=" * 60)
            print(f"   🏙️  CROWD PSYCHOLOGY STATE ENGINE | {local_time}")
            print(f"   📍  {loc.get('name', 'Unknown')}")
            print("=" * 60)
            
            print(f"\n📊 TELEMETRY")
            print(f"   {'Signal (Congestion)':<25} : {congestion:.2f}  " + ("(Gridlock)" if congestion > 0.8 else "(Free Flow)" if congestion < 0.2 else ""))
            print(f"   {'Metric (Gradient)':<25} : {compression_gradient:.2f}")
            print(f"   {'Metric (Velocity)':<25} : {velocity_variance:.2f}")
            
            print(f"\n🧠 DIAGNOSIS")
            print(f"   {'STATE':<25} : {state.upper()}")
            print(f"   {'CONFIDENCE':<25} : {int(confidence * 100)}%")
            
            print(f"\n🛡️  INTERVENTIONS")
            if not actions:
                print("   (No specific actions required)")
            for action in actions:
                print(f"   👉 {action}")
            print("-" * 60)
            
            time.sleep(3) # Faster than 5 for demo purposes
            
    except KeyboardInterrupt:
        print("\nSystem shutting down.")

if __name__ == "__main__":
    main()
