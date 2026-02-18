# Crowd Psychology State Engine (CPSE)

## Project Purpose
CPSE is a modular, real-time classification system designed to infer the psychological state of a crowd from non-identifying, privacy-preserving signals. It aims to prevent crowd-related incidents by providing early warnings and non-force intervention recommendations.

## Key Components
- `app.py`: Main Streamlit dashboard and entry point.
- `signals/`: Adapters for external APIs (TomTom, OpenWeather, Geocoder).
- `metrics/`: Physics engines for Crowd Pressure and Turbulence.
- `engine/`: State Machine, Anomaly Detector, and Classifier logic.
- `data_layer/`: Database connection (`database.py`) and Vectorization logic.
- `interventions/`: Rule-based recommendation engine.
- `scripts/`: Database setup (`db_setup.sql`) and maintenance tools.

## Architecture
- **signals**: Fetches data from external APIs (TomTom Flow & Search) or simulation. Includes interactive geocoding.
- **data_layer**: Standardizes inputs into **Crowd State Vectors** for ML/Analytics readiness.
- **metrics**: Computes crowd dynamics like compression gradients and velocity variance.
- **Real-time Traffic Analysis**: Integrates **TomTom Traffic API** for live congestion data.
- **Physics-Based Metrics**: Computes *Compression Gradient* (with $R^2$ quality check) and *Velocity Variance* (Coefficient of Variation) to detect crush risks.
- **Anomaly Detection**: Statistical Z-Score profiling to flag unusual crowd behavior.
- **Admin Dashboard**: Secure database viewer for global telemetry logs.
- **Data Persistence**: Telemetry history stored in **Supabase (PostgreSQL)**.
- **Intervention Engine**: Maps crowd states (e.g., "Agitated") to specific safety protocols.
- **interventions**: Provides actionable recommendations based on state.
- **persistence**: PostgreSQL (Supabase) for long-term telemetry storage.
- **frontend**: Streamlit dashboard with:
    - **Scenario Controls**: Interactive sidebar for simulating Weather, Events, and Infrastructure (Width).
    - **Live Telemetry**: Real-time Speed, Congestion, and computed Velocity Variance.
    - **Anomaly Alerts**: Visual flags for "Unusual Events".
    - **Security**: Single-tenant isolation & Password authentication.

## Setup & Usage

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create a `.streamlit/secrets.toml` file (or set Environment Variables):

```toml
TOMTOM_API_KEY = "your_key_here"
OPENWEATHERMAP_API_KEY = "your_key_here"
APP_PASSWORD = ["admin_password", "user_password"] # First password is Admin
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
```

> **Note**: `APP_PASSWORD` is mandatory. The first password in the list grants **Admin Console** access.

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
- [Deployment Guide](documents/deployment.md): Instructions for deploying to Streamlit Community Cloud.
- [Security Guide](documents/security.md): Multi-user isolation and authentication details.
- [Database Guide](documents/database.md): Schema and setup for Supabase.
