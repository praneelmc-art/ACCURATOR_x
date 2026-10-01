"""
Generator for temperature_ldr_sensor_anomaly_dataset.csv
Generates realistic multi-sensor telemetry with normal operations, warning drifts,
hardware failures, and transient anomaly fluctuations (spikes/glitches).
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_anomaly_dataset(num_samples_per_sensor: int = 400):
    np.random.seed(42)
    
    sensors = [
        {'id': 'T01', 'type': 'Temperature', 'base_ref': 25.0, 'noise_std': 0.3, 'cal_gain': 0.985, 'cal_offset': 0.3, 'unit': 'C'},
        {'id': 'T02', 'type': 'Temperature', 'base_ref': 25.2, 'noise_std': 0.35, 'cal_gain': 0.980, 'cal_offset': 0.45, 'unit': 'C'},
        {'id': 'LDR', 'type': 'Light_LDR', 'base_ref': 120.0, 'noise_std': 4.0, 'cal_gain': 1.000, 'cal_offset': 0.0, 'unit': 'ADC'},
        {'id': 'H01', 'type': 'Humidity', 'base_ref': 52.0, 'noise_std': 0.8, 'cal_gain': 0.9899, 'cal_offset': 0.0079, 'unit': '%RH'},
        {'id': 'H02', 'type': 'Humidity', 'base_ref': 50.5, 'noise_std': 0.9, 'cal_gain': 0.9823, 'cal_offset': 0.3641, 'unit': '%RH'},
        {'id': 'C01', 'type': 'CO2', 'base_ref': 640.0, 'noise_std': 15.0, 'cal_gain': 0.9727, 'cal_offset': 12.41, 'unit': 'ppm'},
        {'id': 'C02', 'type': 'CO2', 'base_ref': 645.0, 'noise_std': 16.0, 'cal_gain': 0.9754, 'cal_offset': 11.11, 'unit': 'ppm'}
    ]
    
    start_time = datetime(2026, 9, 25, 0, 0, 0)
    all_rows = []
    global_idx = 0
    
    for s in sensors:
        s_id = s['id']
        s_type = s['type']
        base = s['base_ref']
        noise = s['noise_std']
        base_gain = s['cal_gain']
        base_offset = s['cal_offset']
        
        # State transitions across timeline:
        # 0 - 55%: Healthy normal operation
        # 55% - 70%: Transient Anomaly fluctuations (sharp 1-2 sample spikes / flash / noise glitches)
        # 70% - 85%: Incipient progressive drift (Warning)
        # 85% - 100%: Severe slope failure (Unhealthy)
        
        for i in range(num_samples_per_sensor):
            pct = i / num_samples_per_sensor
            t = start_time + timedelta(minutes=i * 5)
            
            # Underlying reference physical ground truth
            # Add slow diurnal cycle
            diurnal = np.sin(2 * np.pi * i / 144) * (base * 0.08)
            ref_val = base + diurnal + np.random.normal(0, noise * 0.5)
            
            # Default healthy calibration
            curr_gain = base_gain + np.random.normal(0, 0.002)
            curr_offset = base_offset + np.random.normal(0, noise * 0.1)
            raw_val = ref_val + np.random.normal(0, noise)
            condition = 'healthy'
            is_anomaly = 0
            
            # Anomaly region (transient spikes and momentary fluctuations)
            if 0.52 <= pct < 0.70:
                # Random intermittent anomaly spikes (~35% of samples in this window)
                if np.random.rand() < 0.35:
                    condition = 'anomaly'
                    is_anomaly = 1
                    # Spike types: sudden optical flash (for LDR), draft/burst (for temp/humidity), or ADC transient
                    if s_type == 'Light_LDR':
                        # Flash of light or shadow jump
                        spike_mag = np.random.choice([+400, +650, -90, +800])
                        raw_val = max(10, min(1020, raw_val + spike_mag))
                    elif s_type == 'Temperature':
                        # Heat gun/cold burst spike of +8 to +20 degrees
                        spike_mag = np.random.choice([+8.5, +14.0, +22.0, -10.0])
                        raw_val = raw_val + spike_mag
                    elif s_type == 'Humidity':
                        # Breath puff or momentary condensation spike
                        spike_mag = np.random.choice([+18.0, +28.0, -15.0])
                        raw_val = min(99.0, max(10.0, raw_val + spike_mag))
                    else:
                        # CO2 puff spike
                        spike_mag = np.random.choice([+250.0, +450.0, -180.0])
                        raw_val = raw_val + spike_mag
                    
                    # NOTE: In transient anomaly, the sensor's underlying hardware slope remains healthy!
                    curr_gain = base_gain + np.random.normal(0, 0.005)
                else:
                    condition = 'healthy'
                    is_anomaly = 0
                    
            elif 0.70 <= pct < 0.85:
                # Warning: Incipient progressive calibration slope divergence
                drift_factor = (pct - 0.70) / 0.15  # 0 to 1
                curr_gain = base_gain * (1.0 + 0.09 * drift_factor)  # 5% to 10% drift
                raw_val = ref_val * (1.0 + 0.08 * drift_factor) + np.random.normal(0, noise * 1.5)
                condition = 'warning'
                is_anomaly = 0
                
            elif pct >= 0.85:
                # Unhealthy: Severe slope divergence / hardware breakdown
                severe_factor = (pct - 0.85) / 0.15  # 0 to 1
                curr_gain = base_gain * (1.0 + 0.22 + 0.10 * severe_factor)  # > 20% drift
                raw_val = ref_val * (1.0 + 0.25 + 0.12 * severe_factor) + np.random.normal(0, noise * 3.0)
                condition = 'unhealthy'
                is_anomaly = 0
                
            all_rows.append({
                'sample_index': global_idx,
                'timestamp': t.strftime('%Y-%m-%d %H:%M:%S'),
                'sensor_id': s_id,
                'sensor_type': s_type,
                'raw_value': round(float(raw_val), 3),
                'reference_value': round(float(ref_val), 3),
                'gain': round(float(curr_gain), 5),
                'offset': round(float(curr_offset), 4),
                'condition': condition,
                'is_anomaly': is_anomaly
            })
            global_idx += 1
            
    df = pd.DataFrame(all_rows)
    
    # Engineer metrology features
    df['slope'] = df['gain']
    df['intercept'] = df['offset']
    df['drift_magnitude'] = (df['raw_value'] - df['reference_value']).abs()
    df['signed_drift'] = df['raw_value'] - df['reference_value']
    df['slope_deviation'] = (df['slope'] - 1.0).abs()
    df['relative_error_pct'] = (df['drift_magnitude'] / df['reference_value'].replace(0, 1e-4)) * 100.0
    
    # Grouped rolling statistics per sensor
    grouped = df.groupby('sensor_id')
    df['rolling_slope_mean'] = grouped['slope'].transform(lambda x: x.rolling(5, min_periods=1).mean())
    df['rolling_slope_std'] = grouped['slope'].transform(lambda x: x.rolling(5, min_periods=1).std().fillna(0))
    df['rolling_drift_mean'] = grouped['drift_magnitude'].transform(lambda x: x.rolling(5, min_periods=1).mean())
    df['slope_rate_of_change'] = grouped['slope'].diff().fillna(0)
    
    # Feature for distinguishing transient anomalies:
    # In an anomaly, current drift is huge compared to the rolling baseline drift,
    # whereas rolling_slope_std or previous baseline slope is normal!
    df['spike_ratio'] = df['drift_magnitude'] / (df['rolling_drift_mean'] + 1e-3)
    
    # Round float columns
    float_cols = ['drift_magnitude', 'signed_drift', 'slope_deviation', 'relative_error_pct', 
                  'rolling_slope_mean', 'rolling_slope_std', 'rolling_drift_mean', 'slope_rate_of_change', 'spike_ratio']
    for c in float_cols:
        df[c] = df[c].round(4)
        
    return df

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("[1/2] Generating comprehensive multi-sensor anomaly dataset...")
    df = generate_anomaly_dataset(num_samples_per_sensor=400)
    
    # Total samples = 7 sensors * 400 = 2,800
    print(f"      Total rows: {len(df)}")
    print(f"      Condition distribution:\n{df['condition'].value_counts()}")
    
    # Export to both root and backend
    root_file = os.path.join(base_dir, 'temperature_ldr_sensor_anomaly_dataset.csv')
    backend_file = os.path.join(backend_dir, 'temperature_ldr_sensor_anomaly_dataset.csv')
    
    df.to_csv(root_file, index=False)
    df.to_csv(backend_file, index=False)
    
    print(f"[2/2] Saved dataset to:")
    print(f"      -> {root_file} ({os.path.getsize(root_file):,} bytes)")
    print(f"      -> {backend_file} ({os.path.getsize(backend_file):,} bytes)")
