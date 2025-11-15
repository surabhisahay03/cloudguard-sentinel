import json
import os
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

app = FastAPI(title="CloudGuard Sentinel API", version="1.0.0")
Instrumentator().instrument(app).expose(app)

MODEL_DIR = Path(__file__).resolve().parents[1] / "ml" / "models"
MODEL_PATH = MODEL_DIR / "model_xgb.pkl"
FEATURES_PATH = MODEL_DIR / "feature_list.json"


try:
    model = joblib.load(MODEL_PATH)
    feature_list = json.loads(FEATURES_PATH.read_text())
    MODEL_READY = True
except Exception as e:
    model, feature_list, MODEL_READY = None, None, False
    LOAD_ERR = str(e)


# # Create a registry to hold our custom metrics
# registry = CollectorRegistry()

# Create our custom metrics
PREDICTIONS_TOTAL = Counter("cloudguard_predictions_total", "Total number of predictions made")
LAST_FAILURE_RISK = Gauge("cloudguard_last_failure_risk", "The last predicted failure risk score")

# ✅ --- ADD A NEW METRIC FOR HEALTH CHECKS ---
HEALTH_CHECKS_TOTAL = Counter(
    "cloudguard_health_checks_total", "Total number of health checks performed"
)


class Telemetry(BaseModel):
    air_temp_k: float
    proc_temp_k: float
    rpm: float
    torque_nm: float
    tool_wear_min: float
    TWF: float
    HDF: float
    PWF: float
    OSF: float
    RNF: float
    temp_diff_k: float
    power: float
    type_H: bool
    type_L: bool
    type_M: bool


# --- Health endpoint (your code is good) ---
@app.get("/health")
def health():
    """Basic health check endpoint"""
    HEALTH_CHECKS_TOTAL.inc()
    return {
        "status": "ok" if MODEL_READY else "error",
        "model_loaded": MODEL_READY,
        "model_path": str(MODEL_PATH),
        "feature_list_path": str(FEATURES_PATH),
        "error": None if MODEL_READY else LOAD_ERR,
    }


# --- Prediction endpoint ---
@app.post("/predict")
def predict(tel: Telemetry):
    # Create a 1-row DataFrame in the exact feature order used in training
    df = pd.DataFrame([{**tel.model_dump()}])[feature_list]
    proba = float(model.predict_proba(df)[:, 1][0])
    label = int(proba >= 0.5)

    PREDICTIONS_TOTAL.inc()
    LAST_FAILURE_RISK.set(proba)

    return {"failure_risk": proba, "label": label}


# -------------------------------------------------
# ✅ Run the app
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
