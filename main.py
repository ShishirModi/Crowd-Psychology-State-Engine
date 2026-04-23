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

    # Initialize services
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
            # 1. Fetch full telemetry from TomTom (or simulation fallback)
            telemetry = signal_provider.fetch_telemetry()

            if telemetry is None:
                print("No signal received. Sleeping...")
                time.sleep(2)
                continue

            congestion    = telemetry["congestion"]
            current_speed = telemetry["current_speed"]
            is_simulated  = telemetry.get("is_simulated", False)

            # 2. Update rolling metrics with both congestion and speed
            metrics.update(congestion, current_speed)
            gradient, gradient_quality, gradient_details = metrics.compute_compression_gradient()
            velocity_var, vv_details                     = metrics.compute_velocity_variance()

            # 3. Classify state (full signature matching app.py)
            history_len = len(metrics.congestion_history)
            state, confidence, breakdown = classifier.classify(
                gradient,
                velocity_var,
                anomaly_score=0.0,          # no anomaly detector in CLI mode
                is_simulated=is_simulated,
                history_len=history_len,
                gradient_quality=gradient_quality,
            )

            # 4. Get intervention recommendations
            actions = recommender.get_recommendations(state)

            # 5. Render output
            loc        = signal_provider.location
            local_time = get_local_time(loc.get('lat', 0), loc.get('lon', 0))

            print("\033[2J\033[H", end="")   # clear screen
            print("=" * 60)
            print(f"   CROWD PSYCHOLOGY STATE ENGINE | {local_time}")
            print(f"   Location: {loc.get('name', 'Unknown')}")
            if is_simulated:
                print("   [SIMULATED DATA — API key not configured]")
            print("=" * 60)

            print(f"\nTELEMETRY")
            print(f"   {'Signal (Congestion)':<25} : {congestion:.2f}  " +
                  ("(Gridlock)" if congestion > 0.8 else "(Free Flow)" if congestion < 0.2 else ""))
            print(f"   {'Speed (km/h)':<25} : {current_speed:.1f}")
            print(f"   {'Metric (Gradient)':<25} : {gradient:.2f}")
            print(f"   {'Metric (Velocity Var)':<25} : {velocity_var:.2f}")

            print(f"\nDIAGNOSIS")
            print(f"   {'STATE':<25} : {state.upper()}")
            print(f"   {'CONFIDENCE':<25} : {int(confidence * 100)}%")

            print(f"\nINTERVENTIONS")
            if not actions:
                print("   (No specific actions required)")
            for action in actions:
                print(f"   -> {action}")
            print("-" * 60)

            time.sleep(3)

    except KeyboardInterrupt:
        print("\nSystem shutting down.")

if __name__ == "__main__":
    main()
