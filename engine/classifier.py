"""
Crowd State Classifier — Multi-factor rule-based classification engine.

Classifies crowd dynamics into one of five states based on compression gradient,
velocity variance, anomaly scores, and environmental context. Produces a primary
state label, a numeric confidence score, and a detailed criteria breakdown that
explains exactly how each factor contributed to the final classification.
"""

from utils.config_loader import get_config


# ── Threshold Definitions ────────────────────────────────────────────────────
# Each state boundary is defined by a compression-gradient range.  Velocity
# variance and anomaly scores act as *override* modifiers that can escalate
# (but never de-escalate) the classified state.

STATE_DESCRIPTIONS = {
    "Stable": {
        "label": "Stable",
        "severity": 0,
        "summary": "Normal crowd flow with no signs of compression or turbulence.",
        "color": "#22c55e",
    },
    "Compressing": {
        "label": "Compressing",
        "severity": 1,
        "summary": "Crowd density is rising — early signs of inflow exceeding outflow capacity.",
        "color": "#f59e0b",
    },
    "Volatile": {
        "label": "Volatile",
        "severity": 2,
        "summary": "High compression with potential for rapid state change. Turbulence detected.",
        "color": "#ef4444",
    },
    "Agitated": {
        "label": "Agitated",
        "severity": 3,
        "summary": "Critical crowd state — extreme compression combined with high turbulence.",
        "color": "#9333ea",
    },
    "Fragmenting": {
        "label": "Fragmenting",
        "severity": 2,
        "summary": "Rapid density drop — crowd is dispersing unevenly, risk of stampede at exits.",
        "color": "#06b6d4",
    },
}


class CrowdClassifier:
    """Rule-based crowd-state classifier with rich diagnostic output."""

    def __init__(self):
        self.config = get_config()
        thresholds = self.config.get("thresholds", {}).get("compression_gradient", {})

        self.t_stable = thresholds.get("stable", 0.1)
        self.t_compressing = thresholds.get("compressing", 0.5)
        self.t_volatile = thresholds.get("volatile", 0.8)

        vv_cfg = self.config.get("thresholds", {}).get("velocity_variance", {})
        self.vv_high = vv_cfg.get("high", 2.0)

        # Track previous state for fragmentation detection
        self._prev_gradient = None

    # ──────────────────────────────────────────────────────────────────────
    def classify(
        self,
        compression_gradient,
        velocity_variance=0,
        anomaly_score=0.0,
        is_simulated=False,
        history_len=10,
        gradient_quality=0.5,
        env_weather_risk=0.0,
        env_width_factor=1.0,
        env_event_active=False,
    ):
        """
        Classifies the crowd state and returns a rich result dict.

        Returns
        -------
        tuple(state: str, confidence: float, breakdown: dict)
            breakdown contains per-factor analysis for UI display.
        """
        breakdown = {}

        # ── 1. PRIMARY STATE from Compression Gradient ───────────────────
        state = "Stable"
        base_confidence = 1.0

        if compression_gradient < self.t_stable:
            state = "Stable"
            base_confidence = 0.95
            breakdown["compression_gradient"] = {
                "value": round(compression_gradient, 4),
                "threshold_used": f"< {self.t_stable} (Stable ceiling)",
                "verdict": "Well below compression threshold — free-flowing movement.",
                "rating": "safe",
            }

        elif compression_gradient < self.t_compressing:
            state = "Stable"
            dist = self.t_compressing - compression_gradient
            range_val = self.t_compressing - self.t_stable
            base_confidence = 0.8 + (dist / max(range_val, 0.01)) * 0.1
            pct_through = ((compression_gradient - self.t_stable) / max(range_val, 0.01)) * 100
            breakdown["compression_gradient"] = {
                "value": round(compression_gradient, 4),
                "threshold_used": f"{self.t_stable}–{self.t_compressing} (Transition zone)",
                "verdict": f"In transition zone — {pct_through:.0f}% toward Compressing threshold.",
                "rating": "watch",
            }

        elif compression_gradient < self.t_volatile:
            state = "Compressing"
            midpoint = (self.t_compressing + self.t_volatile) / 2
            dist_norm = abs(compression_gradient - midpoint) / max(
                (self.t_volatile - self.t_compressing) / 2, 0.01
            )
            base_confidence = 0.9 - (dist_norm * 0.2)
            breakdown["compression_gradient"] = {
                "value": round(compression_gradient, 4),
                "threshold_used": f"{self.t_compressing}–{self.t_volatile} (Compressing band)",
                "verdict": "Active compression — density rising faster than outflow can absorb.",
                "rating": "warning",
            }

        else:
            state = "Volatile"
            base_confidence = 0.9
            if compression_gradient > 0.95:
                state = "Agitated"
                base_confidence = 0.95
            breakdown["compression_gradient"] = {
                "value": round(compression_gradient, 4),
                "threshold_used": f"> {self.t_volatile} (Critical zone)",
                "verdict": "Extreme compression — immediate risk of crowd crush.",
                "rating": "critical",
            }

        # ── 2. FRAGMENTATION DETECTION ───────────────────────────────────
        if self._prev_gradient is not None:
            gradient_delta = compression_gradient - self._prev_gradient
            if gradient_delta < -0.3 and self._prev_gradient > self.t_compressing:
                state = "Fragmenting"
                base_confidence = 0.8
                breakdown["fragmentation"] = {
                    "value": round(gradient_delta, 4),
                    "threshold_used": "Δgradient < −0.3 from elevated state",
                    "verdict": "Rapid density collapse detected — uneven dispersal risk.",
                    "rating": "critical",
                }
        self._prev_gradient = compression_gradient

        # ── 3. VELOCITY VARIANCE Override ────────────────────────────────
        vv_rating = "safe"
        vv_verdict = "Speed distribution is uniform — no stop-and-go shockwaves."

        if velocity_variance > 0.25:
            if state == "Compressing":
                state = "Volatile"
                base_confidence = 0.8
            elif state == "Volatile":
                state = "Agitated"
                base_confidence = 0.85
            else:
                base_confidence -= 0.1
            vv_rating = "critical" if velocity_variance > 0.4 else "warning"
            vv_verdict = (
                f"Coefficient of Variation = {velocity_variance:.2f} "
                f"({'Severe' if velocity_variance > 0.4 else 'Moderate'} turbulence). "
                "Indicates stop-and-go shockwaves that precede crush events."
            )
        elif velocity_variance > 0.10:
            vv_rating = "watch"
            vv_verdict = f"Mild speed variation (CV={velocity_variance:.2f}). Within acceptable range but trending upward."

        breakdown["velocity_variance"] = {
            "value": round(velocity_variance, 4),
            "threshold_used": "CV > 0.25 escalates state; CV > 0.40 = severe",
            "verdict": vv_verdict,
            "rating": vv_rating,
        }

        # ── 4. ANOMALY SCORE Override ────────────────────────────────────
        anomaly_rating = "safe"
        anomaly_verdict = "Crowd vector is within normal statistical bounds."

        if anomaly_score > 2.5:
            if state in ("Stable", "Compressing"):
                state += " (Anomaly Detected)"
                base_confidence -= 0.15
            anomaly_rating = "critical" if anomaly_score > 4.0 else "warning"
            anomaly_verdict = (
                f"Z-Score = {anomaly_score:.2f} exceeds threshold of 2.5. "
                f"{'Extreme statistical outlier — investigate immediately.' if anomaly_score > 4.0 else 'Statistically unusual event detected in crowd vector.'}"
            )
        elif anomaly_score > 1.5:
            anomaly_rating = "watch"
            anomaly_verdict = f"Z-Score = {anomaly_score:.2f}. Elevated but below anomaly threshold (2.5)."

        breakdown["anomaly_score"] = {
            "value": round(anomaly_score, 4),
            "threshold_used": "Z > 2.5 = anomaly; Z > 4.0 = extreme outlier",
            "verdict": anomaly_verdict,
            "rating": anomaly_rating,
        }

        # ── 5. ENVIRONMENTAL MODIFIERS ───────────────────────────────────
        env_penalty = 0.0
        env_notes = []

        if env_weather_risk > 0.5:
            env_penalty += 0.05
            env_notes.append(f"Adverse weather (risk={env_weather_risk:.1f}) reduces visibility & increases slip risk.")
        if env_width_factor < 0.5:
            env_penalty += 0.05
            env_notes.append(f"Narrow passage (width={env_width_factor:.1f}) creates bottleneck amplifying compression.")
        if env_event_active:
            env_penalty += 0.05
            env_notes.append("Active event increases crowd volatility and unpredictable movement.")

        if env_notes:
            # Environmental factors can escalate Compressing → Volatile
            if env_penalty >= 0.1 and state == "Compressing":
                state = "Volatile"
                base_confidence = max(base_confidence - 0.1, 0.5)

        breakdown["environment"] = {
            "weather_risk": round(env_weather_risk, 2),
            "width_factor": round(env_width_factor, 2),
            "event_active": env_event_active,
            "penalty_applied": round(env_penalty, 3),
            "verdict": " | ".join(env_notes) if env_notes else "No adverse environmental conditions.",
            "rating": "warning" if env_penalty >= 0.1 else ("watch" if env_penalty > 0 else "safe"),
        }

        # ── 6. CONFIDENCE ADJUSTMENTS ────────────────────────────────────
        penalties = []
        bonuses = []

        final_confidence = base_confidence - env_penalty

        if is_simulated:
            final_confidence -= 0.20
            penalties.append("Simulated data (−20%)")
        if history_len < 5:
            final_confidence -= 0.30
            penalties.append(f"Warmup phase — only {history_len} samples (−30%)")
        elif history_len < 10:
            final_confidence -= 0.10
            penalties.append(f"Short history — {history_len} samples (−10%)")

        if gradient_quality < 0.5:
            final_confidence -= 0.20
            penalties.append(f"Poor gradient fit R²={gradient_quality:.2f} (−20%)")
        elif gradient_quality < 0.8:
            final_confidence -= 0.10
            penalties.append(f"Moderate gradient fit R²={gradient_quality:.2f} (−10%)")
        elif gradient_quality > 0.95:
            final_confidence += 0.05
            bonuses.append(f"Strong gradient fit R²={gradient_quality:.2f} (+5%)")

        final_confidence = max(0.05, min(1.0, round(final_confidence, 2)))

        breakdown["confidence"] = {
            "base": round(base_confidence, 2),
            "final": final_confidence,
            "penalties": penalties,
            "bonuses": bonuses,
            "verdict": (
                f"Base confidence {base_confidence:.0%} adjusted to {final_confidence:.0%} "
                f"after {len(penalties)} penalty/ies and {len(bonuses)} bonus(es)."
            ),
        }

        # ── 7. COMPOSITE RISK SCORE (0-100) ─────────────────────────────
        risk_score = self._compute_risk_score(
            compression_gradient, velocity_variance, anomaly_score,
            env_weather_risk, env_width_factor, env_event_active
        )
        breakdown["risk_score"] = {
            "value": risk_score,
            "formula": "0.35×Gradient + 0.25×Variance + 0.20×Anomaly + 0.20×Environment",
            "verdict": self._risk_label(risk_score),
            "rating": "critical" if risk_score > 75 else ("warning" if risk_score > 50 else ("watch" if risk_score > 25 else "safe")),
        }

        # ── 8. STATE METADATA ────────────────────────────────────────────
        base_state = state.split(" (")[0]
        state_meta = STATE_DESCRIPTIONS.get(base_state, STATE_DESCRIPTIONS["Stable"])
        breakdown["state_info"] = state_meta

        return state, final_confidence, breakdown

    # ── helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _compute_risk_score(gradient, variance, anomaly, weather, width, event):
        """Weighted composite risk score on a 0–100 scale."""
        g = min(gradient / 1.0, 1.0) * 100
        v = min(variance / 0.5, 1.0) * 100
        a = min(anomaly / 5.0, 1.0) * 100
        e = (weather * 0.4 + (1.0 - min(width, 1.0)) * 0.3 + (1.0 if event else 0.0) * 0.3) * 100
        score = 0.35 * g + 0.25 * v + 0.20 * a + 0.20 * e
        return round(min(100, max(0, score)), 1)

    @staticmethod
    def _risk_label(score):
        if score > 75:
            return f"CRITICAL ({score}/100) — Immediate intervention required."
        elif score > 50:
            return f"HIGH ({score}/100) — Elevated risk, activate contingency plans."
        elif score > 25:
            return f"MODERATE ({score}/100) — Monitor closely, prepare resources."
        else:
            return f"LOW ({score}/100) — Normal operations."
