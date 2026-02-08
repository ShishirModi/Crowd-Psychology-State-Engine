# CPSE Phase Wise Development Plan

## Phase 1: Core Foundation & Basic Logic (Completed)
Established the fundamental architecture, data ingestion from TomTom, and rule-based crowd state classification.

- [x] **Project Setup**
    - [x] Directory structure & Configuration
    - [x] TomTom Traffic API Integration (`signals/tomtom.py`)
    - [x] Metric Computation (`metrics/compression.py`)
    - [x] Rule-based Classifier (`engine/classifier.py`)
    - [x] Intervention Recommender (`interventions/recommender.py`)
- [x] **Frontend**
    - [x] Streamlit Dashboard (`app.py`) with Real-time Map & Metrics.
    - [x] Refinement: Move API Keys to `config.yaml` for flexibility.

## Phase 2: Advanced Analytics & Research Architecture (Completed)
Transitioned to a Vectorized Architecture to support ML readiness and implemented statistical Anomaly Detection to identify "Unusual Events".

- [x] **Data Pipeline Visualization**
    - [x] `CrowdStateVectorizer`: Standardizes signals into vectors `[density, turbulence, pressure, time]`.
    - [x] `Hyper-Local Condition Vectors`: Placeholder for environmental factors.
- [x] **Engine Evolution**
    - [x] `AnomalyDetector`: Rolling window statistical profiling (Z-Score analysis).
    - [x] `GNNModelStub`: Interface for future Graph Neural Network integration.
- [x] **Visual Analysis**
    - [x] UI updates to show Anomaly Scores and "Unusual Event" status.
    - [x] **Verification**
        - [x] Unit Tests for Classifier, Metrics, and Vectorizer.
        - [x] Sanity Check & Code Review.

## Phase 3: Research & AI Integration (Next)
Focus on integrating actual Deep Learning models and Social Physics simulations as per the theoretical framework.

- [ ] **Graph Neural Networks (GNN)**
    - [ ] Implement `STGNN` or `DCRNN` inference in `engine/models`.
    - [ ] Train on historical FCD data (if available) or simulation data.
- [ ] **Social Physics**
    - [ ] Integrate Helbing’s Social Force Model (SFM) for micro-simulations.
    - [ ] Calibrate "Repulsive Force" parameters based on live density.
- [ ] **Predictive Modeling**
    - [ ] Forecast future state (t+15min) based on current Vector trends.
