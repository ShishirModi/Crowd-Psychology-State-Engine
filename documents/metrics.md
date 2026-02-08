# CPSE Metric Reference Guide

This document provides a technical deep-dive into the metrics used by the Crowd Psychology State Engine (CPSE) to classify crowd states.

## 1. Congestion Level
**Type**: Raw Signal -> Normalized Metric
**Source**: TomTom Traffic Flow API
**Update Frequency**: Every 30s (default)

### Formula
$$ C = 1.0 - \frac{v_{current}}{v_{freeflow}} $$

Where:
- $v_{current}$: Real-time average speed of traffic/agents in the segment.
- $v_{freeflow}$: Historic average speed under free-flow conditions.

### Interpretation
- **0.0 - 0.1**: Free flow (Stable).
- **0.1 - 0.5**: Moderate density.
- **0.5 - 0.8**: Heavy traffic / dense crowd.
- **0.8 - 1.0**: Gridlock / Standstill (Critical).

---

## 2. Compression Gradient
**Type**: Derived Metric (Time-Series)
**Source**: Internal Calculation (`metrics/compression.py`)

### Formula
The gradient combines the *absolute* density with the *rate of change*:

$$ G = (w_1 \cdot C_{t}) + (w_2 \cdot \max(0, \frac{dC}{dt} \cdot S)) $$

Where:
- $C_t$: Current Congestion Level.
- $dC/dt$: Slope of congestion over the last 12 samples (60s).
- $w_1, w_2$: Weights (currently 0.6 and 0.4).
- $S$: Scaling factor (5.0) to make slope impact comparable to absolute level.

### Purpose
Detects **rapid inflow shocks**. A high gradient means the crowd is densifying faster than the specific location can naturally dissipate, indicating a risk of crush.

---

## 3. Velocity Variance (Turbulence)
**Type**: Derived Metric (Statistical)
**Source**: Internal Calculation (`metrics/compression.py`) based on TomTom Speed History.

### Formula
$$ Var(v) = \frac{1}{N} \sum_{i=1}^{N} (v_i - \mu)^2 $$

Where:
- $v_i$: Speed sample at time $i$.
- $\mu$: Mean speed over the window (N=12 samples).

### Purpose
Measures **flow stability**.
- **Low Variance**: Smooth, laminar flow (even if slow).
- **High Variance**: Stop-and-go waves, erratic movement. High variance at high density is a precursor to "Crowd Quakes" or stamped behaviors (`Fragmenting` state).

---

## 4. Anomaly Score
**Type**: Statistical Profile
**Source**: `engine/anomaly.py`

### Formula
Standard Z-Score calculated against a rolling window of the last 50 data points.

$$ Z = \frac{X - \mu_{history}}{\sigma_{history}} $$

Where:
- $X$: Current State Vector Magnitude.
- $\sigma$: Standard Deviation of the history.

### Confidence & Initialization
- **Initialization**: Requires ~20 data points (approx. 10 mins) to build a statistically significant baseline. Until then, score is 0.0.
- **Threshold**: Scores > 2.5 are flagged as "Unusual Events".
- **Impact**: If an anomaly is detected, the Classifier's **Confidence Score** is capped at 50% for standard states, reflecting uncertainty about the unusual condition.

---

## 5. Environmental Vectors
**Type**: Contextual Input
**Source**: OpenWeatherMap API + Manual Scenario Controls.

These factors modulate the interpretation of the core metrics.

| Factor | Range | Source | Impact |
|:---|:---|:---|:---|
| **Passage Width** | 0.1 (Alley) - 2.0 (Plaza) | Manual Slider | Multiplier for effective density (Planned). |
| **Weather Risk** | 0.0 (Clear) - 1.0 (Storm) | OpenWeatherMap | Increases perceived stress in the crowd model. |
| **Event Risk** | 0.0 (None) - 1.0 (Protest) | PredictHQ / Manual | Contextual flag that lowers the threshold for 'Volatile' state. |

---

## 6. Confidence Score
**Type**: Meta-Metric
**Source**: `engine/classifier.py`

A distinct probability score (0.0 - 1.0) indicating how well the current data fits the classified state prototype.

- **Stable**: 0.90+ (Clear signal).
- **Compressing**: 0.60 - 0.80 (Transition zones).
- **Volatile**: 0.80+ (Strong signals of distress).
- **Anomaly**: Capped at 0.50 (System unsure due to statistical deviation).
