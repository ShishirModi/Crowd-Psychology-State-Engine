# Crowd Psychology State Engine (CPSE) — v2.0

## Project Overview

The **Crowd Psychology State Engine (CPSE)** is a modular, real-time analytical system that infers the psychological and physical state of a crowd using non-identifying, privacy-preserving environmental signals. Rather than relying on invasive facial recognition or surveillance cameras, CPSE processes aggregate telemetry — traffic flows, congestion indices, weather patterns, and environmental constraints — to compute physical crowd dynamics. It identifies early indicators of crowd-crush risks, turbulence, and agitation, and delivers structured, severity-graded intervention plans for safety personnel.

CPSE is designed for deployment on **Streamlit Community Cloud** and features an enterprise-grade dark-theme dashboard with real-time monitoring, composite risk scoring, per-metric criteria breakdowns, and an administrative database viewer.

---

## Key Features

### Real-Time Signal Fusion
CPSE ingests data from the **TomTom Traffic Flow API** and **OpenWeatherMap API** with automatic fallback to high-fidelity stochastic simulation when API keys are unavailable. The system recalculates every telemetry cycle (configurable, default 30 seconds) and persists results to **Neon PostgreSQL** for long-term trend analysis.

### Physics-Based Crowd Metrics with Full Diagnostics
Two primary metrics drive classification, each returning a detailed sub-metric breakdown for transparency:

- **Compression Gradient**: Combines current density level (60% weight) with the slope of a least-squares linear regression over a 60-second rolling window (40% weight). Returns R² fit quality, slope per sample, slope per minute, trend direction (Rising/Falling/Flat), and a plain-language verdict.
- **Velocity Variance (Coefficient of Variation)**: Detects stop-and-go shockwaves by computing σ(speed)/μ(speed) over the speed history buffer. Returns mean speed, standard deviation, speed range, and a turbulence-level classification (Negligible, Mild, Moderate, Severe).

### Multi-Factor State Classification with Breakdown
The classifier evaluates compression gradient, velocity variance, anomaly score, and environmental conditions to produce one of five crowd states: **Stable**, **Compressing**, **Volatile**, **Agitated**, or **Fragmenting**. Each classification returns a rich `breakdown` dictionary containing per-factor verdicts, threshold comparisons, and color-coded ratings (`safe`, `watch`, `warning`, `critical`).

The classifier also produces a **Composite Risk Score (0–100)** using the weighted formula:

```
Risk = 0.35 × Gradient + 0.25 × Variance + 0.20 × Anomaly + 0.20 × Environment
```

### Statistical Anomaly Detection with Per-Feature Diagnostics
A rolling Z-Score profiler maintains a 100-sample history window. Once calibrated (20+ samples), it computes per-feature Z-Scores across the crowd state vector `[density, turbulence, pressure, time_factor]` and flags features exceeding the 2.5σ threshold. The UI displays a per-feature bar chart and detail table showing each feature's current value, baseline mean, baseline σ, Z-Score, and outlier status.

### Structured Intervention Plans
The recommender maps each crowd state to a tiered response plan. Each action includes a priority level (Critical, High, Medium, Low), a responsible party (Incident Commander, Crowd Control, Gate Teams, etc.), and an expected outcome. The dashboard renders these as priority-colored cards with an overall response-level badge (ROUTINE, ADVISORY, URGENT, EMERGENCY, CAUTION).

### Enterprise-Grade Dashboard
The Streamlit frontend uses a custom dark-theme design system built on the Inter typeface with a slate color palette. Key UI components include:

- **State banner** with gradient background, state label, description, and confidence percentage
- **Composite risk bar** with gradient fill and real-time severity verdict
- **Criteria panels** beside every metric showing thresholds, formulas, current values, and plain-language verdicts — color-coded by severity
- **Dual-panel Plotly charts** (density/compression + turbulence/anomaly) with threshold reference lines
- **Gauge dial** for composite risk score with color-graded zones
- **Donut chart** showing state distribution over the monitoring session
- **Per-feature anomaly bar chart** with outlier highlighting
- **Intervention cards** with priority, owner, and outcome metadata
- **Confidence breakdown expander** listing all penalties and bonuses applied

### Secure Telemetry Persistence
All telemetry streams to **Neon PostgreSQL** utilizing connection pooling for optimal real-time performance. An admin dashboard provides filtered querying by location, record limit, and anomaly-only mode, with CSV export and professional Plotly trend charts.

### Privacy-by-Design
CPSE captures only aggregate macro-flows. No personally identifiable information (PII) or individualized tracking metrics are collected or retained. All classifications are produced by transparent, explainable rule-based logic.

---

## Architecture

```
Crowd-Psychology-State-Engine/
├── app.py                      # Streamlit enterprise dashboard (main entry point)
├── main.py                     # CLI fallback for headless monitoring
├── config.yaml                 # API keys, thresholds, location defaults
├── requirements.txt            # Python dependencies
│
├── signals/                    # External API adapters
│   ├── tomtom.py               #   TomTom Traffic Flow API client
│   ├── weather.py              #   OpenWeatherMap integration
│   └── geocoder.py             #   TomTom Search geocoding
│
├── metrics/                    # Physics-based metric computation
│   └── compression.py          #   Compression gradient + velocity variance
│
├── engine/                     # Core analysis logic
│   ├── classifier.py           #   Multi-factor state classifier with breakdown
│   ├── anomaly.py              #   Z-Score anomaly detector with per-feature diagnostics
│   └── models/
│       └── gnn_stub.py         #   Graph Neural Network placeholder (future)
│
├── data_layer/                 # Persistence & vectorization
│   ├── database.py             #   Neon PostgreSQL client
│   └── vectorizer.py           #   State & environmental vector creation
│
├── interventions/              # Response planning
│   └── recommender.py          #   Severity-graded intervention recommender
│
├── utils/                      # Shared utilities
│   ├── config_loader.py        #   YAML config loader with caching
│   ├── security.py             #   API key redaction
│   └── time_helper.py          #   Timezone-aware time formatting
│
├── tests/                      # Unit tests (15 tests)
│   ├── test_classifier.py      #   Classifier states, overrides, breakdown structure
│   ├── test_metrics.py         #   Gradient computation, velocity variance, details
│   └── test_vectorizer.py      #   Vector shape and normalization
│
├── scripts/                    # Database setup
│   ├── db_setup.sql            #   PostgreSQL schema creation
│   ├── harden_db.sql           #   Row-level security hardening
│   └── check_db.py             #   Database validation
│
└── documents/                  # Extended documentation
    ├── phase_plan.md           #   Development roadmap
    ├── metrics.md              #   Metric definitions & formulas
    ├── database.md             #   Database architecture
    ├── deployment.md           #   Deployment instructions
    └── security.md             #   Security & privacy design
```

---

## Setup & Installation

### 1. Requirements

Python 3.9+ is required. Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configuration & Secrets

Create a `.streamlit/secrets.toml` file or set the following as environment variables:

```toml
TOMTOM_API_KEY = "your_tomtom_traffic_api_key"
OPENWEATHERMAP_API_KEY = "your_openweathermap_api_key"
APP_PASSWORD = ["admin_password", "viewer_password"]
NEON_PASS = "your_neon_db_password"
```

The first password in `APP_PASSWORD` grants Admin Console access (database viewer). Subsequent passwords provide standard monitoring access. If no password is configured, the system defaults to `cpseisawesome` for local development.

All API keys are optional — the system falls back to simulation mode when keys are missing, with a confidence penalty clearly shown in the dashboard.

### 3. Running the Application

**Web Dashboard** (primary):
```bash
streamlit run app.py
```

**CLI Mode** (headless monitoring):
```bash
python main.py
```

### 4. Running Tests

CPSE ships with 15 unit tests covering the classifier, metrics engine, and vectorizer:

```bash
python -m unittest discover tests -v
```

---

## Crowd States

| State | Severity | Trigger | Response Level |
|---|---|---|---|
| **Stable** | 0 | Gradient < 0.1 | ROUTINE |
| **Compressing** | 1 | 0.5 ≤ Gradient < 0.8 | ADVISORY |
| **Volatile** | 2 | Gradient ≥ 0.8, or Compressing + high turbulence | URGENT |
| **Agitated** | 3 | Gradient > 0.95, or Volatile + high turbulence | EMERGENCY |
| **Fragmenting** | 2 | Rapid gradient drop (Δ < −0.3) from elevated state | CAUTION |

The classifier applies velocity variance overrides (CV > 0.25 escalates one severity tier) and anomaly overrides (Z > 2.5 appends an anomaly flag). Environmental modifiers — adverse weather, narrow passages, and active events — can further escalate Compressing into Volatile when their combined penalty exceeds 0.1.

---

## Design Philosophy

- **Anti-Surveillance**: The system uses only aggregate macro-flows. Individual identities do not exist in the CPSE data domain.
- **Explainability**: Every classification comes with a full breakdown — thresholds used, formulas applied, penalties assessed, and plain-language verdicts. Safety decisions require transparency.
- **Advisory Only**: CPSE provides structured recommendations to human operators. It does not actuate physical controls or automate enforcement decisions.
- **Graceful Degradation**: Missing API keys, short history windows, and poor gradient fits are all handled with clearly communicated confidence penalties rather than errors.

---

## Documentation

- [Technical Report](technical_report.md) — Engineering details, mathematical models, confidence scoring, and visualization architecture
- [Phase Plan](documents/phase_plan.md) — Development roadmap
- [Metrics Guide](documents/metrics.md) — Metric definitions and formulas
- [Database Architecture](documents/database.md) — Schema, indexing, and persistence design
- [Security & Privacy](documents/security.md) — API key management, and privacy guarantees
