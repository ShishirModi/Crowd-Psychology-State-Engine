"""
Crowd Metrics — Physics-based compression gradient and velocity variance.

Maintains a rolling history of congestion and speed telemetry and computes
two primary metrics used by the classifier:

1. **Compression Gradient**: Rate-of-change of crowd density, combining
   the current level with the slope of recent history (linear regression).
2. **Velocity Variance**: Coefficient of Variation of speed history,
   detecting stop-and-go shockwaves (turbulence).

Both metrics expose a detailed breakdown dict for UI display.
"""

import numpy as np
from collections import deque


class CrowdMetrics:
    """Rolling-window crowd dynamics calculator."""

    def __init__(self, history_size=12):
        # 12 samples × 5-second intervals = 60-second rolling window
        self.congestion_history = deque(maxlen=history_size)
        self.speed_history = deque(maxlen=history_size)
        self.history_size = history_size

    # ──────────────────────────────────────────────────────────────────────
    def update(self, congestion_level, current_speed=None):
        """Append a new telemetry sample to the rolling buffers."""
        if congestion_level is not None:
            self.congestion_history.append(float(congestion_level))
        if current_speed is not None:
            self.speed_history.append(float(current_speed))

    # ──────────────────────────────────────────────────────────────────────
    def compute_compression_gradient(self):
        """
        Compute the compression gradient with quality metrics.

        Returns
        -------
        gradient : float  (0.0–1.0)
        fit_quality : float  (R², 0.0–1.0)
        details : dict  with sub-metrics for UI
        """
        details = {
            "history_depth": len(self.congestion_history),
            "window_seconds": len(self.congestion_history) * 5,
            "max_window_seconds": self.history_size * 5,
        }

        if len(self.congestion_history) < 2:
            details.update({
                "current_level": 0.0,
                "slope": 0.0,
                "fit_quality_r2": 0.5,
                "weighted_metric": 0.0,
                "method": "insufficient_data",
                "verdict": "Collecting initial samples — need at least 2 data points.",
            })
            return 0.0, 0.5, details

        data = np.array(self.congestion_history)
        current_level = float(data[-1])
        avg_level = float(np.mean(data))
        min_level = float(np.min(data))
        max_level = float(np.max(data))

        fit_quality = 0.5
        slope = 0.0

        if len(data) >= 5:
            x = np.arange(len(data))
            coeffs, residuals, rank, sv, rcond = np.polyfit(x, data, 1, full=True)

            if len(residuals) > 0:
                ss_res = residuals[0]
                ss_tot = np.sum((data - np.mean(data)) ** 2)
                if ss_tot > 1e-6:
                    r_squared = 1 - (ss_res / ss_tot)
                    fit_quality = max(0.0, min(1.0, r_squared))
                else:
                    fit_quality = 1.0
            else:
                fit_quality = 1.0

            slope = coeffs[0]
            method = "linear_regression"
        else:
            slope = data[-1] - data[-2]
            fit_quality = 0.5
            method = "finite_difference"

        w_level = 0.6
        w_slope = 0.4
        metric = (w_level * current_level) + (w_slope * slope * 5)
        metric = max(0.0, min(1.0, metric))

        # Trend direction
        if slope > 0.02:
            trend = "Rising"
        elif slope < -0.02:
            trend = "Falling"
        else:
            trend = "Flat"

        details.update({
            "current_level": round(current_level, 4),
            "average_level": round(avg_level, 4),
            "min_level": round(min_level, 4),
            "max_level": round(max_level, 4),
            "slope": round(slope, 6),
            "slope_per_minute": round(slope * 12, 4),  # 12 samples/min
            "fit_quality_r2": round(fit_quality, 4),
            "weighted_metric": round(metric, 4),
            "weight_current": w_level,
            "weight_slope": w_slope,
            "method": method,
            "trend": trend,
            "verdict": (
                f"Density {trend.lower()} (slope={slope:+.4f}/sample). "
                f"Current={current_level:.2f}, Avg={avg_level:.2f}. "
                f"R²={fit_quality:.2f} ({'strong' if fit_quality > 0.8 else 'moderate' if fit_quality > 0.5 else 'weak'} fit)."
            ),
        })

        return metric, fit_quality, details

    # ──────────────────────────────────────────────────────────────────────
    def compute_velocity_variance(self):
        """
        Compute the velocity variance (Coefficient of Variation).

        Returns
        -------
        cv : float
        details : dict  with sub-metrics for UI
        """
        details = {
            "history_depth": len(self.speed_history),
            "window_seconds": len(self.speed_history) * 5,
        }

        if len(self.speed_history) < 3:
            details.update({
                "mean_speed": 0.0,
                "std_dev": 0.0,
                "cv": 0.0,
                "min_speed": 0.0,
                "max_speed": 0.0,
                "method": "insufficient_data",
                "verdict": "Collecting speed samples — need at least 3.",
            })
            return 0.0, details

        speeds = np.array(self.speed_history)
        mean_speed = float(np.mean(speeds))
        std_dev = float(np.std(speeds))
        min_speed = float(np.min(speeds))
        max_speed = float(np.max(speeds))
        speed_range = max_speed - min_speed

        if mean_speed < 1.0:
            cv = float(std_dev)
            method = "raw_stddev (near-zero mean)"
        else:
            cv = std_dev / mean_speed
            method = "coefficient_of_variation"

        # Turbulence assessment
        if cv > 0.40:
            turb_level = "Severe"
        elif cv > 0.25:
            turb_level = "Moderate"
        elif cv > 0.10:
            turb_level = "Mild"
        else:
            turb_level = "Negligible"

        details.update({
            "mean_speed": round(mean_speed, 2),
            "std_dev": round(std_dev, 2),
            "cv": round(cv, 4),
            "min_speed": round(min_speed, 2),
            "max_speed": round(max_speed, 2),
            "speed_range": round(speed_range, 2),
            "turbulence_level": turb_level,
            "method": method,
            "verdict": (
                f"{turb_level} turbulence (CV={cv:.3f}). "
                f"Speed range {min_speed:.1f}–{max_speed:.1f} km/h, "
                f"σ={std_dev:.2f}, μ={mean_speed:.2f}."
            ),
        })

        return float(cv), details
