"""
Machine Learning Service for Sensor Failure & Calibration Pattern Prediction.
Provides real-time inference using the Random Forest model trained on calibration_slope_dataset.csv.
"""

import os
import json
import collections
import pandas as pd
import numpy as np
import joblib
from calibration import CALIBRATION_MODELS, EXPECTED_SENSORS, HEALTH_BASELINES

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'calibration_rf_model.joblib')
METADATA_PATH = os.path.join(MODELS_DIR, 'model_metadata.json')

class SensorFailurePredictor:
    def __init__(self):
        self.model = None
        self.metadata = {}
        self.history = collections.defaultdict(lambda: collections.deque(maxlen=10))
        self.load_model()

    def load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print(f"[ML SERVICE] Loaded Random Forest model from {MODEL_PATH}")
            except Exception as e:
                print(f"[ML SERVICE ERROR] Failed to load model: {e}")
                self.model = None

        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, 'r') as f:
                    self.metadata = json.load(f)
                print(f"[ML SERVICE] Loaded model metadata. Performance: {self.metadata.get('performance', {})}")
            except Exception as e:
                print(f"[ML SERVICE ERROR] Failed to load metadata: {e}")

    def predict(self, sensor_id: str, raw_value: float, gain: float = None, offset: float = None, sensor_type: str = None):
        """
        Predict future sensor failure risk, condition, and detected calibration pattern.
        """
        # Resolve sensor type
        if not sensor_type:
            if sensor_id in EXPECTED_SENSORS:
                sensor_type = EXPECTED_SENSORS[sensor_id]
            elif sensor_id.startswith('T'):
                sensor_type = 'Temperature'
            elif sensor_id.startswith('H'):
                sensor_type = 'Humidity'
            elif sensor_id.startswith('C'):
                sensor_type = 'CO2'
            else:
                sensor_type = 'Humidity'

        # Resolve gain (slope) and offset (intercept)
        if gain is None or offset is None:
            if sensor_id in CALIBRATION_MODELS:
                cm = CALIBRATION_MODELS[sensor_id]
                gain = gain if gain is not None else cm['gain']
                offset = offset if offset is not None else cm['offset']
            else:
                gain = gain if gain is not None else 1.0
                offset = offset if offset is not None else 0.0

        # Resolve reference benchmark baseline
        baseline = HEALTH_BASELINES.get(sensor_id, {'mean': raw_value, 'std': 1.0})
        ref_mean = baseline['mean']

        # Compute empirical reference value & drift
        calibrated_value = gain * raw_value + offset
        drift_magnitude = abs(raw_value - ref_mean)
        signed_drift = raw_value - ref_mean
        slope_deviation = abs(gain - 1.0)
        relative_error_pct = (drift_magnitude / max(abs(ref_mean), 1e-4)) * 100.0

        # Update sensor history buffer (for rolling graph pattern metrics)
        buf = self.history[sensor_id]
        buf.append({
            'slope': gain,
            'drift': drift_magnitude,
            'raw': raw_value
        })

        slopes = [p['slope'] for p in buf]
        drifts = [p['drift'] for p in buf]

        rolling_slope_mean = float(np.mean(slopes))
        rolling_slope_std = float(np.std(slopes)) if len(slopes) > 1 else 0.0
        rolling_drift_mean = float(np.mean(drifts))
        slope_rate_of_change = float(slopes[-1] - slopes[-2]) if len(slopes) > 1 else 0.0
        spike_ratio = float(drift_magnitude / (rolling_drift_mean + 1e-3))

        # Build feature DataFrame matching model pipeline schema
        feature_dict = {
            'sensor_type': [sensor_type],
            'raw_value': [float(raw_value)],
            'slope': [float(gain)],
            'intercept': [float(offset)],
            'slope_deviation': [float(slope_deviation)],
            'relative_error_pct': [float(relative_error_pct)],
            'rolling_slope_mean': [rolling_slope_mean],
            'rolling_slope_std': [rolling_slope_std],
            'rolling_drift_mean': [rolling_drift_mean],
            'slope_rate_of_change': [slope_rate_of_change],
            'spike_ratio': [spike_ratio]
        }
        X_df = pd.DataFrame(feature_dict)

        # Fallback heuristic if model not loaded
        if self.model is None:
            if spike_ratio > 3.0 and slope_deviation < 0.05:
                pred_condition = 'anomaly'
                prob_healthy = 0.05
                prob_warning = 0.05
                prob_unhealthy = 0.05
                prob_anomaly = 0.85
            elif slope_deviation >= 0.18 or relative_error_pct >= 18.0:
                pred_condition = 'unhealthy'
                prob_unhealthy = 0.95
                prob_warning = 0.03
                prob_healthy = 0.01
                prob_anomaly = 0.01
            elif slope_deviation >= 0.05 or relative_error_pct >= 5.0:
                pred_condition = 'warning'
                prob_warning = 0.80
                prob_unhealthy = 0.10
                prob_healthy = 0.08
                prob_anomaly = 0.02
            else:
                pred_condition = 'healthy'
                prob_healthy = 0.95
                prob_warning = 0.02
                prob_unhealthy = 0.01
                prob_anomaly = 0.02
            probs_map = {'healthy': prob_healthy, 'warning': prob_warning, 'unhealthy': prob_unhealthy, 'anomaly': prob_anomaly}
        else:
            pred_condition = self.model.predict(X_df)[0]
            pred_probs = self.model.predict_proba(X_df)[0]
            classes = list(self.model.named_steps['classifier'].classes_)
            probs_map = {cls_name: round(float(p), 4) for cls_name, p in zip(classes, pred_probs)}

        # Failure Risk Score: calibrated probability of true degradation/failure (0 - 100%)
        # Note: If condition is anomaly (transient spike), failure risk is kept LOW to avoid false alarms!
        p_warning = probs_map.get('warning', 0.0)
        p_unhealthy = probs_map.get('unhealthy', 0.0)
        
        if pred_condition == 'anomaly':
            failure_risk_pct = 4.2
        else:
            failure_risk_pct = round(min(100.0, (p_warning * 0.65 + p_unhealthy * 1.0) * 100.0), 2)

        # Diagnose pattern and determine early failure warning
        is_anomaly = (pred_condition == 'anomaly')
        if is_anomaly:
            risk_level = "TRANSIENT_ANOMALY"
            pattern_title = "Transient Anomaly Fluctuation (Ignored)"
            pattern_description = (
                f"Transient anomaly fluctuation detected (spike ratio={spike_ratio:.2f}). "
                f"Instantaneous fluctuation isolated while underlying calibration slope (m={gain:.4f}) is healthy. "
                f"System filtered out this fluctuation to prevent false alarms."
            )
            time_to_failure = "> 500 operating hours (Nominal)"
            recommendation = "Transient anomaly fluctuation identified and ignored. Normal operation."
            action = "ignore"
        elif pred_condition == 'healthy' and failure_risk_pct < 20.0:
            risk_level = "LOW_RISK"
            pattern_title = "Nominal Linear Baseline"
            pattern_description = (
                f"Calibration slope (m={gain:.4f}) is closely aligned with ideal baseline (deviation={slope_deviation:.4f}). "
                f"Low noise jitter (σ={rolling_slope_std:.4f}). Sensor operating within optimal parameters."
            )
            time_to_failure = "> 500 operating hours (Stable)"
            recommendation = "Normal operation. No maintenance required."
            action = "monitor"
        elif pred_condition == 'warning' or (20.0 <= failure_risk_pct < 75.0):
            risk_level = "EARLY_DRIFT_WARNING"
            pattern_title = "Incipient Calibration Slope Divergence"
            pattern_description = (
                f"Early warning pattern detected: calibration slope (m={gain:.4f}) has shifted by "
                f"{slope_deviation * 100:.2f}% from nominal with rising slope volatility. "
                f"Relative drift is {relative_error_pct:.2f}%."
            )
            time_to_failure = "24 - 48 operating hours (Imminent Drift)"
            recommendation = "Schedule recalibration or sensor check before measurement fidelity drops further."
            action = "schedule_inspection"
        else:
            risk_level = "CRITICAL_FAILURE_IMMINENT"
            pattern_title = "Severe Slope Divergence / Hardware Fault"
            pattern_description = (
                f"Critical failure pattern: calibration slope (m={gain:.4f}) exceeds acceptable tolerance "
                f"(+{slope_deviation * 100:.2f}% divergence). Measurement outputs are no longer trustworthy."
            )
            time_to_failure = "< 4 operating hours (Critical Failure)"
            recommendation = "Replace or recalibrate sensor immediately to prevent downstream operational errors."
            action = "replace_sensor"

        return {
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "raw_value": round(float(raw_value), 4),
            "calibrated_value": round(float(calibrated_value), 4),
            "slope": round(float(gain), 4),
            "intercept": round(float(offset), 4),
            "slope_deviation": round(float(slope_deviation), 4),
            "drift_magnitude": round(float(drift_magnitude), 4),
            "relative_error_pct": round(float(relative_error_pct), 2),
            "rolling_slope_mean": round(float(rolling_slope_mean), 4),
            "rolling_slope_std": round(float(rolling_slope_std), 4),
            "spike_ratio": round(float(spike_ratio), 4),
            "ml_prediction": {
                "predicted_condition": pred_condition,
                "is_anomaly": is_anomaly,
                "action": action,
                "failure_risk_pct": failure_risk_pct,
                "risk_level": risk_level,
                "class_probabilities": probs_map,
                "pattern_title": pattern_title,
                "pattern_description": pattern_description,
                "estimated_time_to_failure": time_to_failure,
                "recommendation": recommendation
            }
        }

# Global singleton
ml_predictor = SensorFailurePredictor()
