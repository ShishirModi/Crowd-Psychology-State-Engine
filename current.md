# CPSE Current System State

## 1. Project Overview
**Name**: Crowd Psychology State Engine (CPSE)
**Purpose**: Real-time crowd state classification system using non-identifying signals to prevent crowd incidents.
**Core Philosophy**: Privacy-first, Non-force Intervention, Rule-based Explainability.

## 2. Architecture & Modules

### **2.1 Signals (`signals/`)**
- **Primary Source**: TomTom Flow Segment Data API.
- **Implementation**: `signals/tomtom.py`
- **Configuration**:
    - **Method**: Environment Variable (`TOMTOM_API_KEY`).
    - **Current Target**: Delhi City Center (28.6139, 77.2090).
    - **Logic**: Fetches `currentSpeed` and `freeFlowSpeed` to calculate a `congestion` ratio (0.0 - 1.0).
- **Fallback**: Built-in simulation (Random walk + sine wave bias) if API key is missing or calls fail.

### **2.2 Metrics (`metrics/`)**
- **Processing**: `metrics/compression.py`
- **Metric 1: Compression Gradient**:
    - **Logic**: Combines absolute density value (60% weight) with the rate of change/slope (40% weight).
    - **Purpose**: Detect rapid density increases.
- **Metric 2: Velocity Variance**:
    - **Input**: Real-time speed history from TomTom.
    - **Logic**: Calculates statistical variance of speed over the last 60 seconds.
    - **Purpose**: Detect stop-and-go waves (Turbulence) indicative of 'Fragmenting' state.

### **2.3 Engine (`engine/`)**
- **Classifier**: `engine/classifier.py`
- **Logic**: Rule-based system with Anomaly Awareness.
- **States**:
    1.  **Stable**: Low compression (< 0.1).
    2.  **Compressing**: Medium compression (0.1 - 0.5).
    3.  **Volatile**: High compression (0.5 - 0.8).
    4.  **Agitated**: Very High compression (> 0.95).
    5.  **Fragmenting**: High velocity variance (> 2.0).
- **Anomaly Detection**: Z-Score profiling of state vectors. Flags "Unusual Events" if Z > 2.5.

### **2.4 Environmental Context**
- **Weather**: Live data via **OpenWeatherMap API** (`signals/weather.py`).
- **Manual Controls**: Sidebar sliders for Passage Width, Weather Override, and Event Status.

### **2.5 Interventions (`interventions/`)**
- **Recommender**: `interventions/recommender.py`
- **Mapping**: Context-aware recommendations based on current state.

### **2.6 Configuration (`config.yaml`)**
- **API**: Maps environment variable names (e.g., `TOMTOM_API_KEY`) to internal providers.
- **Thresholds**: Tunable values for state boundaries.

## 3. Operational Status
- **Current Mode**: **LIVE** (Connected to TomTom & OpenWeatherMap).
- **Last Verification**: 2026-02-06
- **Result**: System fully functional. Unit tests passed (9/9).
- **Dependencies**: `requests`, `pandas`, `numpy`, `streamlit`, `javascript`.

## 4. Workflows
1.  **Main Loop (`app.py`)**:
    - Initialize Signal Providers (TomTom, Weather).
    - Loop (Interval: 30s):
        - Fetch Telemetry & Weather -> Update Metrics -> Detect Anomaly -> Classify -> Recommend -> Render UI.

## 5. Known Limitations
- **Granularity**: TomTom provides segment-averaged speed, so "Variance" is temporal variance of the average, not spatial variance of individual agents.
- **Prediction**: No forward-looking LSTM model yet (planned for Phase 3).
