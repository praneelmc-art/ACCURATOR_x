from pydantic import BaseModel
from typing import Optional


class SensorData(BaseModel):
    id: str
    parameter: str
    raw_value: float
    corrected_value: Optional[float] = None
    drift: float = 0
    health: float = 100
    weight: float = 1
    status: str = "healthy"