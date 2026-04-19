# Technical Report: Crowd Psychology State Engine (CPSE)

## 1. Executive Summary
The **Crowd Psychology State Engine (CPSE)** is an advanced, real-time behavioral analytical framework designed to identify early-warning indicators of crowd turbulence, crush risks, and severe psychological agitation. In contrast to high-surveillance facial recognition tools, CPSE relies wholly on non-personally identifiable information (PII)—utilizing aggregate macroeconomic traffic flows, topological constraints, and weather patterns.

**Deployment Context:** The CPSE frontend application architecture is built to be hosted seamlessly on **Streamlit Community Cloud**, serving as the primary multi-user interaction dashboard and database administrative viewer.

---

## 2. System Architecture & Workflows
CPSE utilizes a decoupled, component-driven approach allowing for modular upgrades to specific signal ingesters or metric computations.

### 2.1 The Application Layer (`app.py` & `main.py`)
- **Dashboard (Streamlit)**: Acts as the primary orchestrator. Authenticates users, fetches location data, triggers the signal ingestion process, and visually plots telemetry via `plotly` charting libraries.
- **State Management**: Streamlit `session_state` creates strong isolation between different users. Dedicated sessions manage `history`, `metrics`, and `anomaly_detector` states.
- **Role-Based Access**: Single-tenant application passwords. Users connecting with the primary administrative password gain access to raw underlying PostgreSQL datastore telemetry dumps.

### 2.2 Signal Ingestion Layer (`signals/`)
- **TomTom Traffic Adapter**: Ingests immediate real-world network data. Extracts variables like `free_flow_speed` and `current_speed`. Derives `congestion` geometrically based on velocity deltas.
- **OpenWeatherMap Integration**: Live weather parameters evaluate the friction effect. Adverse weather dramatically influences a crowd's "irritation" or risk of stampede.
- **Simulation Fallback**: If external API limitations are met, the engine smoothly falls back to a stochastically driven simulation engine. 

---

## 3. Mathematical Models & Metrics Computing
Located in `metrics/compression.py`, this layer transforms rudimentary API numbers into physical mechanics.

### 3.1 Compression Gradient ($d/dt$)
Represents the velocity of density change. Surges indicate rapid inflow without corresponding outflow.
- **Methodology**: CPSE models the compression gradient by analyzing moving `deque` arrays of congestion data. It calculates the slope utilizing **Linear Regression (Polyfit)**.
- **Goodness of Fit Check**: The validity of the gradient computes an accompanying $R^2$ check. If $R^2$ is low (noisy data), the subsequent state classification heavily penalizes `Base_Confidence`.

### 3.2 Velocity Variance (Turbulence)
Represents stop-and-go shockwaves synonymous with crowd crushes. 
- **Methodology**: Evaluates the Standard Deviation ($\sigma$) of the recorded speed history, normalized as a **Coefficient of Variation** ($CV = \frac{\sigma}{\mu}$). A high CV suggests extreme physical turbulence despite high or low underlying average speed.

---

## 4. Analytical Engine & Classification
The core intellect spans `classifier.py` and `anomaly.py`.

### 4.1 Statistical Anomaly Detection (Z-Score)
Identifies deviations from recent historical equilibriums dynamically.
- Maintains a robust historical tensor window of vectorized multidimensional properties.
- Normalizes vectors and determines anomalies strictly if $Z \text{-Score} = \left|\frac{X - \mu}{\sigma}\right| > 2.5$.
- Eliminates the need for monolithic ML training data by establishing localized baselines (e.g. Times Square features vastly different baseline parameters compared to a rural intersection).

### 4.2 State Machine Classification
Employs an intuitive rule-machine designed to output Explainable AI (XAI) determinations.

1. **Stable**: Baseline gradient parameters. Routine state.
2. **Compressing**: Sustained, steep compression gradients observed in ingress points.
3. **Volatile**: High compression levels merged with elevated systemic anomaly scores.
4. **Agitated**: Extreme compression factors interlinked intrinsically with extreme *Velocity Variance* (high turbulence CV score).
5. *(Fragmenting)*: Indicates sudden rapid density reductions accompanying high speeds, potentially implying mass panic dispersal.

**Confidence Decay Rules**:
The system establishes a `1.0` confidence basis, dynamically decaying based on environmental factors:
- `Is Simulated`: $\downarrow -0.2$
- `Short Warmup (History < 5)`: $\downarrow -0.3$
- `Low Gradient Linearity (R^2 < 0.8)`: $\downarrow -0.15$

---

## 5. Storage & Persistence Context
Located in `data_layer/database.py`, raw vectors compute output telemetry that streams directly to **Supabase**.
- Contains real-time insertions pushing location names, speeds, $Z$-scores, and classified states alongside UNIX timestamps.
- **Scalability**: Decoupling compute (Streamlit Community Cloud) from persistence (Supabase Postgres) facilitates virtually infinite horizontal scale for telemetry storage independently of web requests. Extracted data forms the bedrock for potential future Graph Neural Networks (GNN) implementation.
