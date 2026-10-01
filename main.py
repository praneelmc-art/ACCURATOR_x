import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from supabase_client import supabase
from schemas import SensorData
from calibration import (
    CALIBRATION_MODELS,
    EXPECTED_SENSORS,
    calibrate,
    health_from_raw,
)
from ml_service import ml_predictor

app = FastAPI(title="Accurator AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_INDEX = os.path.join(os.path.dirname(__file__), "static", "index.html")


class BatchSensorData(BaseModel):
    sensors: list[SensorData]


class FailurePredictionRequest(BaseModel):
    sensor_id: Optional[str] = "H01"
    raw_value: float = 50.0
    gain: Optional[float] = None
    slope: Optional[float] = None
    offset: Optional[float] = None
    intercept: Optional[float] = None
    sensor_type: Optional[str] = None


def process_sensor(sensor: SensorData):
    """Automatically calibrate, assess, and run ML failure prediction on one sensor."""

    if sensor.id not in EXPECTED_SENSORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown sensor ID: {sensor.id}. "
                   f"Expected: {sorted(EXPECTED_SENSORS)}",
        )

    expected_parameter = EXPECTED_SENSORS[sensor.id]

    if sensor.parameter.lower() != expected_parameter.lower():
        raise HTTPException(
            status_code=400,
            detail=(
                f"{sensor.id} must use parameter '{expected_parameter}', "
                f"received '{sensor.parameter}'"
            ),
        )

    raw = float(sensor.raw_value)

    # Automatic calibration:
    # corrected_value = gain * raw_value + offset
    corrected, gain, offset = calibrate(sensor.id, raw)

    # Automatic health/status — no manual status required.
    health, status, anomaly_score = health_from_raw(sensor.id, raw)

    # Calibration correction magnitude.
    drift = abs(raw - corrected)

    # Sensor confidence follows health.
    weight = health / 100.0

    # Random Forest ML Early Failure & Slope Pattern Prediction
    ml_res = ml_predictor.predict(
        sensor_id=sensor.id,
        raw_value=raw,
        gain=gain,
        offset=offset,
        sensor_type=expected_parameter
    )

    return {
        "id": sensor.id,
        "parameter": sensor.parameter,
        "raw_value": raw,
        "corrected_value": round(corrected, 4),
        "drift": round(drift, 4),
        "health": health,
        "weight": round(weight, 4),
        "status": status,
        "calibration_gain": gain,
        "calibration_offset": offset,
        "anomaly_score": anomaly_score,
        "ml_failure_prediction": ml_res["ml_prediction"],
        "slope_metrics": {
            "slope": ml_res["slope"],
            "slope_deviation": ml_res["slope_deviation"],
            "rolling_slope_mean": ml_res["rolling_slope_mean"],
            "rolling_slope_std": ml_res["rolling_slope_std"],
            "relative_error_pct": ml_res["relative_error_pct"]
        }
    }


@app.get("/")
def root():
    if os.path.exists(STATIC_INDEX):
        return FileResponse(STATIC_INDEX)
    return {
        "project": "Accurator AI",
        "status": "Backend running successfully",
        "calibration": "automatic",
        "sensors": sorted(EXPECTED_SENSORS),
    }


@app.get("/dashboard")
def dashboard():
    if os.path.exists(STATIC_INDEX):
        return FileResponse(STATIC_INDEX)
    raise HTTPException(status_code=404, detail="Dashboard UI not found")


@app.get("/api")
def api_status():
    return {
        "project": "Accurator AI",
        "status": "Backend running successfully",
        "calibration": "automatic",
        "sensors": sorted(EXPECTED_SENSORS),
    }


@app.get("/test-supabase")
def test_supabase():
    response = supabase.table("sensors").select("*").limit(5).execute()

    return {
        "status": "Supabase connected successfully",
        "records": response.data,
    }


@app.get("/calibration")
def get_calibration_models():
    """Show the learned gain/offset used by the backend."""
    return {
        "formula": "calibrated_value = gain * raw_value + offset",
        "models": CALIBRATION_MODELS,
    }


@app.get("/ml/model-info")
def get_ml_model_info():
    """Return trained Random Forest model metadata, accuracy, and feature importances."""
    return {
        "status": "ready" if ml_predictor.model is not None else "model_not_found",
        "metadata": ml_predictor.metadata
    }


@app.get("/ml/reload")
def reload_ml_model():
    """Reload the updated Random Forest model from disk."""
    ml_predictor.load_model()
    return {
        "status": "reloaded",
        "model_loaded": ml_predictor.model is not None,
        "classes": getattr(ml_predictor.model.named_steps.get('classifier', None), 'classes_', []).tolist() if ml_predictor.model else []
    }


@app.get("/dataset/temperature_ldr_sensor_anomaly_dataset.csv")
@app.get("/api/dataset/temperature_ldr_sensor_anomaly_dataset.csv")
def download_anomaly_dataset():
    """Download the temperature_ldr_sensor_anomaly_dataset.csv file."""
    csv_path = os.path.join(os.path.dirname(__file__), "temperature_ldr_sensor_anomaly_dataset.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temperature_ldr_sensor_anomaly_dataset.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    return FileResponse(
        path=csv_path,
        filename="temperature_ldr_sensor_anomaly_dataset.csv",
        media_type="text/csv"
    )


@app.post("/predict-failure")
def predict_sensor_failure(req: FailurePredictionRequest):
    """
    Run Random Forest inference on calibration slope & graph patterns
    to predict early sensor failures and failure risk probabilities.
    """
    try:
        gain_val = req.gain if req.gain is not None else req.slope
        offset_val = req.offset if req.offset is not None else req.intercept
        prediction = ml_predictor.predict(
            sensor_id=req.sensor_id or "H01",
            raw_value=req.raw_value,
            gain=gain_val,
            offset=offset_val,
            sensor_type=req.sensor_type
        )
        return {
            "status": "success",
            "prediction": prediction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sensors")
def create_sensor(sensor: SensorData):
    try:
        processed = process_sensor(sensor)

        # Only columns that already exist in Supabase are written.
        db_data = {
            "id": processed["id"],
            "parameter": processed["parameter"],
            "raw_value": processed["raw_value"],
            "corrected_value": processed["corrected_value"],
            "drift": processed["drift"],
            "health": processed["health"],
            "weight": processed["weight"],
            "status": processed["status"],
        }

        response = (
            supabase
            .table("sensors")
            .upsert(db_data)
            .execute()
        )

        return {
            "status": "success",
            "message": "Sensor calibrated and saved successfully",
            "sensor": processed,
            "database": response.data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sensors/batch")
def create_sensors_batch(batch: BatchSensorData):
    """Process and save all six sensors automatically."""

    try:
        expected_ids = set(EXPECTED_SENSORS)

        if len(batch.sensors) != 6:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Expected exactly 6 sensors "
                    "(T01, T02, H01, H02, C01, C02), "
                    f"received {len(batch.sensors)}"
                ),
            )

        received_ids = {sensor.id for sensor in batch.sensors}

        if received_ids != expected_ids:
            missing = sorted(expected_ids - received_ids)
            extra = sorted(received_ids - expected_ids)

            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "Batch must contain T01, T02, H01, H02, C01 and C02"
                    ),
                    "missing": missing,
                    "unexpected": extra,
                },
            )

        # Automatic calibration + health analysis for all six.
        processed = [
            process_sensor(sensor)
            for sensor in batch.sensors
        ]

        db_data = [
            {
                "id": s["id"],
                "parameter": s["parameter"],
                "raw_value": s["raw_value"],
                "corrected_value": s["corrected_value"],
                "drift": s["drift"],
                "health": s["health"],
                "weight": s["weight"],
                "status": s["status"],
            }
            for s in processed
        ]

        response = (
            supabase
            .table("sensors")
            .upsert(db_data)
            .execute()
        )

        return {
            "status": "success",
            "message": "All 6 sensors calibrated and saved successfully",
            "count": len(processed),
            "sensors": processed,
            "database": response.data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
