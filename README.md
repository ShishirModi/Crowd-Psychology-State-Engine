# Crowd Psychology State Engine (CPSE)

## Project Purpose
CPSE is a modular, real-time classification system designed to infer the psychological state of a crowd from non-identifying, privacy-preserving signals. It aims to prevent crowd-related incidents by providing early warnings and non-force intervention recommendations.

## Architecture
- **signals**: Fetches data from external APIs (TomTom Flow & Search) or simulation. Includes interactive geocoding.
- **data_layer**: Standardizes inputs into **Crowd State Vectors** for ML/Analytics readiness.
- **metrics**: Computes crowd dynamics like compression gradients and velocity variance.
- **engine**: 
    - **Classifier**: Rule-based state classification (Stable, Compressing, Volatile).
    - **AnomalyDetector**: Statistical profiling to flag "Unusual Events" (High Z-Score).
    - **Models**: Stubbed interface for future GNN/Social Physics models.
- **interventions**: Provides actionable recommendations based on state.
- **frontend**: Streamlit dashboard with:
    - **Scenario Controls**: Interactive sidebar for simulating Weather, Events, and Infrastructure (Width).
    - **Live Telemetry**: Real-time Speed, Congestion, and computed Velocity Variance.
    - **Anomaly Alerts**: Visual flags for "Unusual Events".

## Setup & Usage

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
Set the following environment variables (names are configurable in `config.yaml`):
- `TOMTOM_API_KEY`: Required for Traffic Data & Geocoding.
- `OPENWEATHERMAP_API_KEY`: Required for live Weather conditions.

### 3. Run

#### CLI Mode
Interactively select location and monitor via terminal:
```bash
python main.py
```

#### Web Dashboard (Frontend)
Launch the visual dashboard:
```bash
streamlit run app.py
```

### 4. Testing
Run the unit test suite:
```bash
python -m unittest discover tests
```

## Design Philosophy
- **Privacy First**: No PII is collected. only aggregate flow data.
- **Explainable**: Rule-based logic ensures transparency in classification.
- **Advisory**: The system provides recommendations, not automated enforcement.

## Documentation
- [Phase Plan](documents/phase_plan.md): Development roadmap.
- [Sanity Check](documents/sanity_check.md): Latest code review and security audit.
- [Metrics Guide](documents/metrics.md): Detailed explanation of all system metrics and formulas.
