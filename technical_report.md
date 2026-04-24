# Technical Report: Crowd Psychology State Engine (CPSE) — v2.0

## 1. Executive Summary

The **Crowd Psychology State Engine (CPSE)** is an advanced, real-time behavioral analytical framework designed to identify early-warning indicators of crowd turbulence, crush risks, and severe psychological agitation. In contrast to high-surveillance facial recognition tools, CPSE relies wholly on non-personally identifiable information (PII) — utilizing aggregate macroscopic traffic flows, topological constraints, and weather patterns.

Version 2.0 introduces a comprehensive refactoring of the analysis engine and dashboard. Key additions include a multi-factor classifier that produces per-parameter diagnostic breakdowns, a composite risk scoring formula, per-feature anomaly diagnostics, severity-graded structured intervention plans, and an enterprise-grade dark-theme dashboard with professional Plotly visualizations.

**Deployment Context:** The frontend is built for **Streamlit Community Cloud**, serving as the primary multi-user interaction dashboard and database administrative viewer.

---

## 2. System Architecture & Data Flow

CPSE employs a decoupled, component-driven architecture. Each module has a clearly defined interface, enabling independent upgrades to signal adapters, metric computations, or classification logic without cascading changes.

### 2.1 Application Layer

**`app.py`** — the Streamlit enterprise dashboard — acts as the primary orchestrator. It authenticates users, manages session-scoped state (history buffers, metric engines, anomaly detectors), triggers signal ingestion, runs the analysis pipeline, and renders the full dashboard layout.

**State Management:** Streamlit `session_state` isolates data between concurrent users. Each session maintains its own `CrowdMetrics`, `AnomalyDetector`, `CrowdStateVectorizer`, telemetry history buffer, and location context.

**Role-Based Access:** A password-gated login screen supports multiple passwords. The first password in the configuration list grants Admin Console access, which exposes the database viewer with filtered querying, trend charts, and CSV export. Subsequent passwords provide standard monitoring access. Passwords are compared using constant-time `secrets.compare_digest` to prevent timing attacks.

**`main.py`** provides a headless CLI fallback for terminal-based monitoring without the Streamlit runtime.

### 2.2 Signal Ingestion Layer (`signals/`)

**TomTom Traffic Adapter (`tomtom.py`)**
Ingests real-world traffic flow data for the monitored coordinates. Extracts `free_flow_speed` and `current_speed` from the TomTom Flow Segment Data API (v4). Derives congestion geometrically:

$$
\text{congestion} = 1.0 - \frac{\text{current\_speed}}{\text{free\_flow\_speed}}
$$

The result is clamped to [0.0, 1.0]. A zero or negative free-flow speed triggers a 50 km/h fallback default.

**OpenWeatherMap Integration (`weather.py`)**
Maps the OpenWeatherMap condition ID to a risk factor on a 0.0–1.0 scale. The mapping covers all standard weather groups: Thunderstorm (1.0), Heavy Rain (0.8), Snow (0.7), Light/Moderate Rain (0.5), Atmospheric conditions like fog (0.4), Drizzle (0.3), Clouds (0.1), and Clear (0.0). Tornado and Squall conditions receive dedicated elevated scores (1.0 and 0.9 respectively).

**Simulation Fallback**
When API keys are unavailable or requests fail, the system generates stochastic telemetry biased toward moderate congestion (base 0.5 ± noise). Simulated data carries a clearly flagged `is_simulated: true` marker that triggers a −20% confidence penalty in the classifier and a toast notification in the dashboard.

**Geocoder (`geocoder.py`)**
Provides location search via the TomTom Search API (v2), returning candidate locations with coordinates for dynamic monitoring target selection.

---

## 3. Mathematical Models & Metrics

Located in `metrics/compression.py`, the metrics layer transforms raw API telemetry into physics-based crowd dynamics indicators. Both metrics now return a detailed sub-metric dictionary alongside their primary value, enabling full transparency in the dashboard.

### 3.1 Compression Gradient

Represents the rate of density change — surges indicate rapid inflow without corresponding outflow capacity.

**Methodology:**
CPSE maintains a rolling `deque` of congestion samples (default: 12 samples × 5-second intervals = 60-second window). The gradient metric is a weighted combination of the current congestion level and its rate of change:

$$
\text{metric} = 0.6 \times \text{current\_level} + 0.4 \times \text{slope} \times 5
$$

The slope is computed via least-squares linear regression (`numpy.polyfit`, degree 1) when 5+ samples are available. For shorter histories, a simple finite difference (last two points) is used.

**Quality Assessment (R²):**
The goodness-of-fit is computed as:

$$
R^2 = 1 - \frac{SS_{res}}{SS_{tot}}
$$

This R² value flows into the classifier's confidence scoring. A low R² (noisy data) incurs a confidence penalty, while R² > 0.95 earns a small bonus.

**Returned Sub-Metrics:**
The `details` dictionary includes: `current_level`, `average_level`, `min_level`, `max_level`, `slope` (per sample), `slope_per_minute`, `fit_quality_r2`, `trend` (Rising/Falling/Flat), `method` (linear_regression or finite_difference), `history_depth`, `window_seconds`, and a human-readable `verdict`.

### 3.2 Velocity Variance (Turbulence)

Detects stop-and-go shockwaves that are characteristic precursors to crowd-crush events.

**Methodology:**
Computes the **Coefficient of Variation (CV)** across the speed history buffer:

$$
CV = \frac{\sigma(\text{speed})}{\mu(\text{speed})}
$$

When mean speed is near zero (< 1.0 km/h), the raw standard deviation is used instead, as the CV becomes undefined.

**Turbulence Classification:**

| CV Range | Level | Classifier Impact |
|---|---|---|
| < 0.10 | Negligible | None |
| 0.10 – 0.25 | Mild | Watch status in UI |
| 0.25 – 0.40 | Moderate | Escalates state one tier |
| > 0.40 | Severe | Escalates + critical rating |

**Returned Sub-Metrics:**
The `details` dictionary includes: `mean_speed`, `std_dev`, `cv`, `min_speed`, `max_speed`, `speed_range`, `turbulence_level`, `method`, and a human-readable `verdict`.

---

## 4. Analytical Engine & Classification

### 4.1 Statistical Anomaly Detection (`engine/anomaly.py`)

Identifies deviations from recent historical equilibrium using per-feature Z-Score analysis.

**Mechanism:**
The detector maintains a rolling history of crowd state vectors (default: 100 samples). After a calibration phase (minimum 20 samples), each new vector is compared against the historical distribution:

$$
Z_i = \frac{|X_i - \mu_i|}{\sigma_i} \quad \text{for each feature } i
$$

The aggregate anomaly score is the **maximum** Z-Score across all features:

$$
\text{anomaly\_score} = \max(Z_1, Z_2, \ldots, Z_n)
$$

An anomaly is flagged when `anomaly_score > 2.5`. A score exceeding 4.0 is classified as an extreme outlier.

**Per-Feature Diagnostics (v2.0):**
The detector now returns a `per_feature` list in its details dictionary. Each entry contains: `feature` name (density, turbulence, pressure, time_factor), `value` (current), `mean` (baseline μ), `std` (baseline σ), `z_score`, and `is_outlier` (boolean). This enables the dashboard to render a per-feature bar chart highlighting which specific aspects of the crowd state are deviating from baseline.

**Calibration Feedback:**
During the warmup phase, the detector reports `calibration_pct` — a percentage indicating how close the system is to having enough samples for reliable detection. This is displayed in the UI criteria panel.

### 4.2 Multi-Factor State Classifier (`engine/classifier.py`)

The classifier is the core analytical intelligence of CPSE. It produces an Explainable AI (XAI) classification with a full diagnostic breakdown.

**State Definitions:**

| State | Severity | Primary Trigger |
|---|---|---|
| Stable | 0 | Gradient < 0.1 |
| Compressing | 1 | 0.5 ≤ Gradient < 0.8 |
| Volatile | 2 | Gradient ≥ 0.8 |
| Agitated | 3 | Gradient > 0.95 or Volatile + turbulence |
| Fragmenting | 2 | Rapid gradient drop (Δ < −0.3) from elevated state |

**Classification Pipeline (8 stages):**

1. **Primary State from Compression Gradient** — Gradient value is compared against configured thresholds (stable: 0.1, compressing: 0.5, volatile: 0.8). In the transition zone between stable and compressing (0.1–0.5), the system reports how far through the zone the gradient has progressed as a percentage.

2. **Fragmentation Detection** — Compares the current gradient against the previous cycle. A drop exceeding −0.3 from an elevated state (above compressing threshold) triggers the Fragmenting classification.

3. **Velocity Variance Override** — A CV > 0.25 escalates the state by one tier (Compressing → Volatile, Volatile → Agitated). This captures cases where density is moderate but movement patterns are dangerously turbulent.

4. **Anomaly Score Override** — A Z-Score > 2.5 appends "(Anomaly Detected)" to Stable or Compressing states and reduces confidence by 15%.

5. **Environmental Modifiers** — Weather risk > 0.5, passage width < 0.5, and active events each contribute a 5% penalty. If the combined environmental penalty reaches 10%, Compressing is escalated to Volatile.

6. **Confidence Adjustments** — The base confidence (0.0–1.0) is adjusted by:

   | Condition | Adjustment |
   |---|---|
   | Simulated data | −20% |
   | History < 5 samples | −30% |
   | History 5–9 samples | −10% |
   | Gradient R² < 0.5 | −20% |
   | Gradient R² 0.5–0.8 | −10% |
   | Gradient R² > 0.95 | +5% |
   | Environmental penalty | −(penalty %) |

   Final confidence is clamped to [0.05, 1.0].

7. **Composite Risk Score** — A weighted aggregate on a 0–100 scale:

   $$
   \text{Risk} = 0.35 \times G + 0.25 \times V + 0.20 \times A + 0.20 \times E
   $$

   Where:
   - $G = \min(\text{gradient} / 1.0, 1) \times 100$
   - $V = \min(\text{variance} / 0.5, 1) \times 100$
   - $A = \min(\text{anomaly} / 5.0, 1) \times 100$
   - $E = (0.4 \times \text{weather} + 0.3 \times (1 - \text{width}) + 0.3 \times \text{event}) \times 100$

   Risk labels: LOW (0–25), MODERATE (25–50), HIGH (50–75), CRITICAL (75–100).

8. **State Metadata** — The final output includes the state description, severity level, summary text, and associated color code from the `STATE_DESCRIPTIONS` registry.

**Breakdown Dictionary:**
Every classification returns a `breakdown` dict with keys: `compression_gradient`, `velocity_variance`, `anomaly_score`, `environment`, `confidence`, `risk_score`, and `state_info`. Each entry contains the metric value, threshold used, a rating (`safe`/`watch`/`warning`/`critical`), and a plain-language verdict. This powers the criteria panels displayed beside each metric in the dashboard.

---

## 5. Intervention Planning (`interventions/recommender.py`)

The recommender maps classified states to structured response plans. Each plan includes:

- **Response Level**: ROUTINE, ADVISORY, URGENT, EMERGENCY, or CAUTION
- **Level Color & Icon**: For dashboard rendering
- **Action List**: Each action specifies:
  - **Priority**: Critical, High, Medium, or Low
  - **Action**: The specific intervention instruction
  - **Owner**: The responsible party (Incident Commander, Crowd Control, Gate Teams, Field Stewards, Communications, Operations, Emergency Services)
  - **Outcome**: The expected result of executing the action

The dashboard renders actions as priority-colored cards (red for Critical, orange for High, yellow for Medium, green for Low) with metadata rows showing priority, owner, and outcome.

---

## 6. Vectorization (`data_layer/vectorizer.py`)

Raw telemetry is transformed into fixed-dimension vectors for anomaly detection and potential future ML applications:

**Crowd State Vector** (4 dimensions):
```
[density, turbulence, pressure, time_factor]
```
- `density`: Congestion level, clipped to [0, 1]
- `turbulence`: Velocity variance / 5.0, clipped to [0, 1]
- `pressure`: Compression gradient, clipped to [−1, 1]
- `time_factor`: Normalized seconds-in-day (0.0 = midnight, 1.0 = 23:59)

**Environmental Vector** (3 dimensions):
```
[passage_width_factor, weather_risk, event_indicator]
```

---

## 7. Storage & Persistence (`data_layer/database.py`)

Telemetry streams to **Neon PostgreSQL** via the `psycopg2` client library. The schema is automatically bootstrapped and migrated. The `crowd_telemetry` table stores: `location_name`, `latitude`, `longitude`, `congestion`, `speed`, `gradient`, `velocity_var`, `anomaly_score`, `state`, `session_id`, and `created_at`.

Indexes on `created_at` (descending) and `location_name` support efficient filtered queries. The connection uses a pooler endpoint to handle multiplexed Streamlit connections effectively.

The admin dashboard provides:
- Filtered querying by location, record limit, and anomaly-only mode
- KPI cards (total records, average congestion, anomalies detected, dominant state)
- Plotly area chart for congestion trend (per-location)
- Formatted data table with progress bars and conditional formatting
- CSV export

---

## 8. Dashboard Visualization Architecture

The v2.0 dashboard uses a custom enterprise CSS theme built on the Inter typeface with a slate/navy color palette. All Plotly charts share a consistent dark theme via a centralized `PLOTLY_LAYOUT` configuration.

### 8.1 State Banner
A full-width gradient bar displaying the current state label, descriptive summary, and confidence percentage. Colors match the state's severity (green → amber → red → purple → cyan).

### 8.2 Composite Risk Bar
A horizontal progress bar with a gradient fill (green → yellow → orange → red), numerical score, severity verdict, and formula footnote.

### 8.3 Metric Cards with Criteria Panels
Four metric columns (Congestion, Gradient, Velocity Variance, Anomaly Score), each with a Streamlit `st.metric` widget above a custom HTML criteria panel. Panels are color-coded by left-border (green=safe, yellow=watch, orange=warning, red=critical) and display 5–8 rows of key-value diagnostic data plus a plain-language verdict.

### 8.4 Signal Telemetry Charts
A dual-panel Plotly subplot:
- **Top panel**: Congestion (blue area fill) and Gradient (amber dotted line)
- **Bottom panel**: Velocity Variance (purple area fill) and Anomaly Z-Score (red dashed line) with a horizontal threshold reference at Z=2.5

### 8.5 Risk Gauge Dial
A Plotly `Indicator` gauge showing the composite risk score (0–100) with four color-graded zones and a critical threshold marker at 75.

### 8.6 State Distribution Donut
A Plotly donut (pie with hole) chart showing the percentage of time spent in each crowd state during the current monitoring session, using the canonical state colors.

### 8.7 Anomaly Feature Breakdown
An expandable section containing a Plotly bar chart of per-feature Z-Scores (with outliers highlighted in red) and a tabular display of each feature's current value, baseline mean, baseline σ, Z-Score, and outlier status.

### 8.8 Intervention Cards
Priority-colored cards (left border matching priority level) with action text, and a metadata row showing priority badge, responsible owner, and expected outcome.

---

## 9. Testing

CPSE maintains 15 unit tests across three test modules:

- **`test_classifier.py`** (8 tests): Stable/Compressing/Volatile/Agitated state classification, anomaly flag behavior, velocity variance override, and breakdown structure validation (risk_score, confidence keys).
- **`test_metrics.py`** (5 tests): Initial state, gradient computation with trend verification, gradient details completeness, steady-speed zero variance, and fluctuating-speed variance detection.
- **`test_vectorizer.py`** (2 tests): State vector shape and value mapping, environmental vector shape and value mapping.

Run the full suite:
```bash
python -m unittest discover tests -v
```

---

## 10. Configuration Reference (`config.yaml`)

```yaml
api:
  tomtom:
    use_env_key: true
    env_key_name: "TOMTOM_API_KEY"
    base_url: "https://api.tomtom.com/traffic/services/4/flowSegmentData"
    search_url: "https://api.tomtom.com/search/2/search"
  openweathermap:
    use_env_key: true
    env_key_name: "OPENWEATHERMAP_API_KEY"
    base_url: "https://api.openweathermap.org/data/2.5/weather"
database:
  type: "neon"
  pooler_host: "ep-aged-cherry-aoxn5nod-pooler.c-2.ap-southeast-1.aws.neon.tech"
  direct_host: "ep-aged-cherry-aoxn5nod.c-2.ap-southeast-1.aws.neon.tech"
  name:        "neondb"
  role:        "neondb_owner"
  port:        5432
  password_env: "NEON_PASS"

location:
  name: "Delhi City Center"
  lat: 28.6139
  lon: 77.2090
  radius: 2000

thresholds:
  compression_gradient:
    stable: 0.1        # Below this → Stable
    compressing: 0.5    # Below this → Stable (transition zone) or Compressing
    volatile: 0.8       # Above this → Volatile or Agitated
  velocity_variance:
    high: 2.0

simulation:
  enabled: true         # Fallback when API keys are missing
```

---

## 11. Future Directions

- **Graph Neural Network (GNN)**: The `engine/models/gnn_stub.py` placeholder is reserved for a future spatial-temporal GNN that models crowd dynamics as a graph of interconnected zones.
- **Multi-Source Signal Fusion**: Integration with additional data sources such as cell-tower density estimates, transit system passenger counts, and social media sentiment feeds.
- **Predictive Classification**: Time-series forecasting models (LSTM/Transformer) trained on persisted telemetry to predict state transitions 5–15 minutes ahead.
- **WebSocket Real-Time Push**: Replace Streamlit's polling-based refresh with WebSocket-driven push updates for sub-second latency.
