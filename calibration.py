"""
Accurator AI learned calibration model.

Formula:
    corrected_value = gain * raw_value + offset

Parameters were learned from healthy samples in sensor_calibration_data.csv.
"""

CALIBRATION_MODELS = {
    'C01': {'gain': 0.9727325430576582, 'offset': 12.414210935298001, 'sensor_type': 'CO2'},
    'C02': {'gain': 0.9753758983092888, 'offset': 11.109280341155454, 'sensor_type': 'CO2'},
    'H01': {'gain': 0.9899108055857887, 'offset': 0.007882670037879791, 'sensor_type': 'Humidity'},
    'H02': {'gain': 0.9822633342300597, 'offset': 0.36406873578926735, 'sensor_type': 'Humidity'},
    'T01': {'gain': 0.9799160871763946, 'offset': 0.2994816184417388, 'sensor_type': 'Temperature'},
    'T02': {'gain': 0.972364299422018, 'offset': 0.4675785397363086, 'sensor_type': 'Temperature'}
}

HEALTH_BASELINES = {
    'C01': {'mean': 643.434075, 'std': 110.54791569887786},
    'C02': {'mean': 640.0857702702702, 'std': 106.28603044054996},
    'H01': {'mean': 50.75059999999999, 'std': 5.711400329043041},
    'H02': {'mean': 47.85988059701492, 'std': 4.727702143883907},
    'T01': {'mean': 25.229975000000003, 'std': 1.4389448236127784},
    'T02': {'mean': 25.039205128205133, 'std': 1.5603787781823781}
}

EXPECTED_SENSORS = {
    "T01": "Temperature",
    "T02": "Temperature",
    "H01": "Humidity",
    "H02": "Humidity",
    "C01": "CO2",
    "C02": "CO2",
}


def calibrate(sensor_id: str, raw_value: float):
    model = CALIBRATION_MODELS[sensor_id]
    corrected = model["gain"] * raw_value + model["offset"]
    return corrected, model["gain"], model["offset"]


def health_from_raw(sensor_id: str, raw_value: float):
    baseline = HEALTH_BASELINES[sensor_id]
    std = max(baseline["std"], 1e-9)

    # Distance from the sensor's learned healthy range.
    z = abs(raw_value - baseline["mean"]) / std

    if z >= 3:
        status = "unhealthy"
    elif z >= 2:
        status = "warning"
    else:
        status = "healthy"

    health = max(
        0.0,
        min(100.0, 100.0 - max(0.0, z - 1.0) * 40.0)
    )

    return round(health, 2), status, round(z, 3)