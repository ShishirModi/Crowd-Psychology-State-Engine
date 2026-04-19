# Crowd Psychology State Engine (CPSE)

## 📌 Project Overview
The **Crowd Psychology State Engine (CPSE)** is a modular, real-time analytical system designed to infer the psychological and physical state of a crowd using non-identifying, privacy-preserving environmental signals. Rather than relying on invasive facial recognition or surveillance cameras, CPSE processes aggregate telemetry (such as traffic flows, congestion indices, and environmental constraints) to compute physical crowd dynamics. It identifies early indicators of crowd-crush risks, turbulence, and agitation, providing actionable deterrence and intervention protocols for safety personnel and law enforcement agencies.

CPSE is natively designed for deployment on the **Streamlit Community Cloud**, featuring a highly interactive, responsive dashboard for real-time monitoring and database administration.

## ✨ Key Features
- **Real-Time Signal Ingestion**: Systematically fuses data from external sources, predominantly the **TomTom Traffic API** and **OpenWeatherMap**, alongside intelligent simulation fallbacks.
- **Physics-Based Crowd Metrics**: Dynamically models density and movement by calculating the **Compression Gradient** (the rate of congestion change over time) and **Velocity Variance** (indicators of crowd turbulence and stop-and-go shockwaves).
- **Statistical Anomaly Detection**: Employs rolling Z-Score profiling across crowd vectors to flag statistically relevant behavioral anomalies without needing massive pre-trained datasets.
- **Explainable Classification Engine**: A robust state-machine evaluation classifies crowds into defined categories (Stable, Compressing, Volatile, Agitated, Fragmenting) paired with dynamically calculated Confidence Scores.
- **Actionable Intervention Recommender**: Maps active crowd states to corresponding rule-based safety recommendations designed to diffuse tension.
- **Secure Telemetry Persistence**: Seamless long-term storage of multi-dimensional state vectors and anomaly logs in **Supabase (PostgreSQL)**, featuring a Single-tenant built-in Admin dashboard.
- **Privacy-by-Design**: Adheres strictly to data minimization principles; absolutely no PII (Personally Identifiable Information) or individualized tracking metrics are captured or retained.

## 🏗️ Modular Architecture
The system is divided into carefully decoupled modules ensuring scalability and testability:

- `app.py`: The main Streamlit web application dashboard and entry point.
- `main.py`: Interactive command-line interface execution (CLI Fallback).
- `signals/`: Adapters and ingestion handlers for external APIs (TomTom Flow, OpenWeatherMap, Geocoder).
- `metrics/`: Physics engines computing foundational metrics using moving history arrays.
- `engine/`: The core logic hub containing the `CrowdClassifier` and `AnomalyDetector`.
- `data_layer/`: Supabase database connection schemas (`database.py`) and vector standardization logic for ingestion limits.
- `interventions/`: Rule-based recommendation engine for rendering outputs.
- `scripts/`: SQL schemas (`db_setup.sql`) and database hardening logic.
- `documents/`: Comprehensive documentation suite detailing phases, DB, and metrics structure.

## ⚙️ Setup & Installation

### 1. Requirements
Ensure you are running **Python 3.9+**. Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configuration & Secrets
For local execution, create a `.streamlit/secrets.toml` file (or set these as system Environment Variables). This secures your external API references and defines access controls.

```toml
TOMTOM_API_KEY = "your_tomtom_traffic_api_key_here"
OPENWEATHERMAP_API_KEY = "your_openweathermap_key_here"
APP_PASSWORD = ["admin_password_1", "user_password_2"] # The first password grants Admin Console access
SUPABASE_URL = "your_supabase_project_url"
SUPABASE_KEY = "your_supabase_api_key"
```

> **Security Note**: `APP_PASSWORD` is completely mandatory. The system relies on this for user auth and role isolation.

### 3. Execution

#### Web Dashboard (Frontend)
Launch the visual dashboard locally. (Note: CPSE is fully ready to be deployed to Streamlit Community Cloud):
```bash
streamlit run app.py
```

#### CLI Mode
Interactively select target locations and monitor telemetry directly via the terminal:
```bash
python main.py
```

### 4. Unit Testing
CPSE maintains a foundational test suite to ensure module integrity:
```bash
python -m unittest discover tests
```

## 🧠 Design & Privacy Philosophy
- **Anti-Surveillance**: The model utilizes aggregate macro-flows. Individual identities simply do not exist within the CPSE data domain.
- **Explainability**: Safety decisions require transparency. Rule-based logical matrices ensure every classification is mathematically explainable.
- **Advisory in Nature**: The system provides actionable *recommendations* to human operators. It does not actuate physical controls or automate enforcement.

## 📚 Extensive Documentation
For comprehensive details, please dive into our specific guides:
- [Technical Report](technical_report.md): In-depth engineering, mathematical logic, and cloud hosting specifications.
- [Phase Plan](documents/phase_plan.md): Historical developmental roadmap.
- [Metrics Guide](documents/metrics.md): Explicit breakdown of system metrics and formulas.
- [Database & Security](documents/security.md): Multi-user isolation, DB schemas, and PostgreSQL architectures.
