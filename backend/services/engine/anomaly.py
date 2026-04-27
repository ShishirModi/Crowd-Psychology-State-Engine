"""
Anomaly Detector — Statistical Z-Score profiling with EMA baseline.

Maintains a rolling history of crowd-state vectors and detects outliers
using per-feature Z-Scores.  Exposes detailed diagnostics for every
detection cycle so the UI can render a full breakdown.
"""

import numpy as np
from collections import deque


class AnomalyDetector:
    """Z-Score anomaly detector with rolling history and diagnostic output."""

    def __init__(self, history_size=100, z_threshold=2.5, min_samples=20):
        self.history_size = history_size
        self.z_threshold = z_threshold
        self.min_samples = min_samples
        self.history = deque(maxlen=history_size)
        self._cycle = 0

    def train(self, historical_vectors):
        """Pre-load history for faster calibration."""
        self.history.extend(historical_vectors)

    def update_and_detect(self, current_vector):
        """
        Update history and check for anomaly.

        Returns
        -------
        is_anomaly : bool
        anomaly_score : float  (max Z-Score across features)
        details : dict  with per-feature breakdown
        """
        self._cycle += 1
        details = {
            "cycle": self._cycle,
            "history_depth": len(self.history),
            "min_required": self.min_samples,
            "threshold": self.z_threshold,
        }

        if len(self.history) < self.min_samples:
            self.history.append(current_vector)
            calibration_pct = (len(self.history) / self.min_samples) * 100
            details.update({
                "status": "calibrating",
                "calibration_pct": round(calibration_pct, 1),
                "verdict": (
                    f"Calibrating baseline — {len(self.history)}/{self.min_samples} samples "
                    f"({calibration_pct:.0f}%). Anomaly detection inactive."
                ),
                "per_feature": [],
            })
            return False, 0.0, details

        hist_array = np.array(self.history)
        mean = np.mean(hist_array, axis=0)
        std = np.std(hist_array, axis=0)
        std_safe = np.where(std < 1e-6, 1e-6, std)

        z_scores = np.abs((current_vector - mean) / std_safe)
        anomaly_score = float(np.max(z_scores))
        mean_z = float(np.mean(z_scores))

        feature_names = ["density", "turbulence", "pressure", "time_factor"]
        per_feature = []
        for i, name in enumerate(feature_names[: len(current_vector)]):
            entry = {
                "feature": name,
                "value": round(float(current_vector[i]), 4),
                "mean": round(float(mean[i]), 4),
                "std": round(float(std[i]), 4),
                "z_score": round(float(z_scores[i]), 4),
                "is_outlier": bool(z_scores[i] > self.z_threshold),
            }
            per_feature.append(entry)

        self.history.append(current_vector)
        is_anomaly = anomaly_score > self.z_threshold

        # Identify which features are driving the anomaly
        outlier_features = [f["feature"] for f in per_feature if f["is_outlier"]]

        if is_anomaly:
            verdict = (
                f"ANOMALY DETECTED — max Z={anomaly_score:.2f} (threshold {self.z_threshold}). "
                f"Outlier features: {', '.join(outlier_features) if outlier_features else 'aggregate'}."
            )
        else:
            verdict = (
                f"Normal — max Z={anomaly_score:.2f}, mean Z={mean_z:.2f}. "
                f"All features within {self.z_threshold}σ of baseline."
            )

        details.update({
            "status": "active",
            "max_z_score": round(anomaly_score, 4),
            "mean_z_score": round(mean_z, 4),
            "is_anomaly": is_anomaly,
            "outlier_features": outlier_features,
            "per_feature": per_feature,
            "verdict": verdict,
        })

        return is_anomaly, float(anomaly_score), details
