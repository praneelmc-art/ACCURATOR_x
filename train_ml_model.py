"""
Train Random Forest Model for Sensor Calibration Pattern & Anomaly Detection.
Trains on temperature_ldr_sensor_anomaly_dataset.csv, handles 4 classes:
  1. healthy (nominal baseline)
  2. warning (progressive calibration drift)
  3. unhealthy (severe hardware divergence / failure)
  4. anomaly (transient spikes / optical flash / thermal glitches - to be ignored)
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

def build_dataset_and_train():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    source_csv = os.path.join(backend_dir, 'temperature_ldr_sensor_anomaly_dataset.csv')
    
    if not os.path.exists(source_csv):
        source_csv = os.path.join(base_dir, 'temperature_ldr_sensor_anomaly_dataset.csv')
    if not os.path.exists(source_csv):
        raise FileNotFoundError(f"Anomaly dataset not found at {source_csv}")
        
    print(f"[1/5] Loading anomaly dataset from {source_csv}...")
    df = pd.read_csv(source_csv)
    print(f"      Total records: {len(df)}")
    print(f"      Classes breakdown:\n{df['condition'].value_counts()}")

    # Verify or compute engineered features
    if 'spike_ratio' not in df.columns:
        df['spike_ratio'] = df['drift_magnitude'] / (df['rolling_drift_mean'] + 1e-3)
        
    # Feature columns for 4-class Random Forest
    feature_cols = [
        'sensor_type',
        'raw_value',
        'slope',
        'intercept',
        'slope_deviation',
        'relative_error_pct',
        'rolling_slope_mean',
        'rolling_slope_std',
        'rolling_drift_mean',
        'slope_rate_of_change',
        'spike_ratio'
    ]

    X = df[feature_cols]
    y = df['condition']

    print("\n[2/5] Splitting data into stratified Train (80%) and Test (20%) sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), ['sensor_type']),
            ('num', 'passthrough', [c for c in feature_cols if c != 'sensor_type'])
        ]
    )

    rf_classifier = RandomForestClassifier(
        n_estimators=120,
        max_depth=10,
        min_samples_leaf=2,
        random_state=42,
        class_weight='balanced'
    )

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', rf_classifier)
    ])

    print("[3/5] Training 4-class Random Forest classifier...")
    pipeline.fit(X_train, y_train)

    # 5-fold cross validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring='f1_macro')

    # Test Evaluation
    y_pred = pipeline.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred)
    test_f1 = f1_score(y_test, y_pred, average='macro')
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(y_test, y_pred)

    print(f"\n[4/5] Model Performance Metrics:")
    print(f"      5-Fold CV Macro F1: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    print(f"      Test Accuracy:      {test_acc * 100:.2f}%")
    print(f"      Test Macro F1:      {test_f1 * 100:.2f}%")
    print("\nClassification Report:\n", report)

    # Extract feature importances
    cat_features = list(pipeline.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out(['sensor_type']))
    num_features = [c for c in feature_cols if c != 'sensor_type']
    all_feature_names = cat_features + num_features
    importances = pipeline.named_steps['classifier'].feature_importances_
    
    feature_importance_dict = {
        name: round(float(imp), 4)
        for name, imp in sorted(zip(all_feature_names, importances), key=lambda x: x[1], reverse=True)
    }

    print("Top Predictive Features:")
    for name, imp in list(feature_importance_dict.items())[:6]:
        print(f"  - {name}: {imp * 100:.2f}%")

    # Export trained model artifacts
    models_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(models_dir, exist_ok=True)

    model_path = os.path.join(models_dir, 'calibration_rf_model.joblib')
    joblib.dump(pipeline, model_path)
    print(f"\n[5/5] Exported trained model to: {model_path}")

    # Metadata & summary
    metadata = {
        "model_name": "RandomForest_Sensor_Failure_And_Anomaly_Detector",
        "algorithm": "RandomForestClassifier",
        "classes": list(pipeline.named_steps['classifier'].classes_),
        "feature_cols": feature_cols,
        "feature_importances": feature_importance_dict,
        "performance": {
            "test_accuracy": round(float(test_acc), 4),
            "test_macro_f1": round(float(test_f1), 4),
            "cv_f1_mean": round(float(cv_scores.mean()), 4),
            "cv_f1_std": round(float(cv_scores.std()), 4),
            "confusion_matrix": cm
        },
        "slope_patterns": {
            "healthy": {
                "typical_slope_range": [0.985, 1.015],
                "typical_slope_deviation": "< 0.02",
                "risk_status": "LOW_RISK"
            },
            "warning": {
                "typical_slope_range": [1.050, 1.120],
                "typical_slope_deviation": "0.05 - 0.12",
                "description": "Incipient calibration drift detected. Sensor response slope shifted ~7-10%. Early failure warning.",
                "risk_status": "EARLY_DRIFT_WARNING"
            },
            "unhealthy": {
                "typical_slope_range": [1.180, 1.450],
                "typical_slope_deviation": "> 0.18",
                "description": "Severe calibration divergence. Sensor slope exceeded operational threshold (+20%). Critical failure.",
                "risk_status": "CRITICAL_FAILURE_IMMINENT"
            },
            "anomaly": {
                "typical_spike_ratio": "> 2.5",
                "typical_slope_deviation": "< 0.03",
                "description": "Transient anomaly fluctuation detected (optical flash / thermal spike / ADC glitch). Underlying calibration curve is healthy. Filtered out and ignored.",
                "risk_status": "TRANSIENT_ANOMALY"
            }
        }
    }

    meta_path = os.path.join(models_dir, 'model_metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"      Exported model metadata to: {meta_path}")

    return metadata

if __name__ == '__main__':
    build_dataset_and_train()
