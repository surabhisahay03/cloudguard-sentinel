import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import boto3
import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

# --- CONFIGURATION ---
# S3 & MLflow Config
LOG_BUCKET_NAME = os.getenv("LOG_BUCKET_NAME", "cloudguard-sentinel-datalogs-surabhi")
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", "http://mlflow-stack-cloudguard.mlflow.svc.cluster.local:5000"
)
MODEL_NAME = "machine-failure-prediction"
MODEL_STAGE = "production"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# Initialize Clients
s3_client = boto3.client("s3", region_name="us-east-1")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloudGuard-Sentinel")

# --- MODEL STATE MANAGEMENT ---
# We use a global state to hold the model so it can be updated in the background
model_state = {"model": None, "version": "N/A", "feature_list": None}

# --- METRICS ---
PREDICTIONS_TOTAL = Counter("cloudguard_predictions_total", "Total number of predictions made")
LAST_FAILURE_RISK = Gauge("cloudguard_last_failure_risk", "The last predicted failure risk score")
HEALTH_CHECKS_TOTAL = Counter(
    "cloudguard_health_checks_total", "Total number of health checks performed"
)
MODEL_UPDATES_TOTAL = Counter(
    "cloudguard_model_updates_total", "Total number of times the model was updated"
)


# --- DATA SCHEMA (Preserved exactly from your file) ---
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


# --- DYNAMIC LOADING LOGIC ---
def load_feature_list():
    """
    Loads the feature list from the local JSON file to ensure column order matches training.
    """
    try:
        # Assuming the JSON file is still baked into the image at this path
        model_dir = Path(__file__).resolve().parents[1] / "ml" / "models"
        features_path = model_dir / "feature_list.json"

        if features_path.exists():
            return json.loads(features_path.read_text())
        else:
            # Fallback hardcoded list if file is missing (Safety net)
            logger.warning("feature_list.json not found! Using hardcoded fallback.")
            return [
                "air_temp_k",
                "proc_temp_k",
                "rpm",
                "torque_nm",
                "tool_wear_min",
                "TWF",
                "HDF",
                "PWF",
                "OSF",
                "RNF",
                "temp_diff_k",
                "power",
                "type_H",
                "type_L",
                "type_M",
            ]
    except Exception as e:
        logger.error(f"Error loading feature list: {e}")
        return []


def load_latest_model():
    """
    Connects to MLflow and loads the latest Production model.
    """

    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.MlflowClient()

        try:
            model_info = client.get_model_version_by_alias(MODEL_NAME, MODEL_STAGE)
        except Exception:
            logger.warning("No model found with alias 'production'")
            return

        latest_version = model_info.version

        # 2. Check if we already have this version
        if model_state["version"] == latest_version and model_state["model"] is not None:
            return  # Already up to date

        # 3. Load the new model
        logger.info(f"⬇️ Found new model (v{latest_version}). Loading...")
        model_uri = f"models:/{MODEL_NAME}@{MODEL_STAGE}"

        # We use sklearn.load_model to preserve 'predict_proba' capability
        loaded_model = mlflow.sklearn.load_model(model_uri)

        # 4. Update State
        model_state["model"] = loaded_model
        model_state["version"] = latest_version
        model_state["feature_list"] = load_feature_list()

        MODEL_UPDATES_TOTAL.inc()
        logger.info(f"✅ Successfully switched to Model v{latest_version}")

    except Exception as e:
        logger.error(f"❌ Failed to refresh model from MLflow: {e}")


def background_model_refresher():
    """Loop to check for updates periodically."""
    while True:
        load_latest_model()
        time.sleep(CHECK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("🚀 Starting CloudGuard Sentinel API (Dynamic Mode)...")

    # Load feature list first
    model_state["feature_list"] = load_feature_list()

    # Attempt initial load (blocking, so we fail fast if MLflow is down,
    # OR we proceed if we want to allow starting without a model)
    load_latest_model()

    # Start background thread
    refresh_thread = threading.Thread(target=background_model_refresher, daemon=True)
    refresh_thread.start()

    yield
    # --- SHUTDOWN ---
    logger.info("🛑 Shutting down API...")


# --- API APP ---
app = FastAPI(title="CloudGuard Sentinel API", version="2.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


# --- ENDPOINTS ---


@app.get("/health")
def health():
    HEALTH_CHECKS_TOTAL.inc()
    is_ready = model_state["model"] is not None
    return {
        "status": "ok" if is_ready else "loading_or_error",
        "model_version": model_state["version"],
        "using_mlflow": True,
    }


@app.post("/predict")
def predict(tel: Telemetry):
    if model_state["model"] is None:
        raise HTTPException(status_code=503, detail="Model is loading or unavailable.")

    # 1. Prepare Data
    # Convert input to DataFrame and enforce column order using feature_list
    try:
        input_data = tel.model_dump()
        df = pd.DataFrame([input_data])

        # Ensure columns are in the exact order the model expects
        if model_state["feature_list"]:
            df = df[model_state["feature_list"]]

    except Exception as e:
        logger.error(f"Data formatting error: {e}")
        raise HTTPException(status_code=400, detail="Invalid feature input")

    # 2. Predict
    # We use predict_proba because your dashboard relies on Risk Scores
    try:
        proba = float(model_state["model"].predict_proba(df)[0][1])
        label = int(proba >= 0.5)

        PREDICTIONS_TOTAL.inc()
        LAST_FAILURE_RISK.set(proba)

    except Exception as e:
        logger.error(f"Prediction inference error: {e}")
        raise HTTPException(status_code=500, detail="Model inference failed")

    # 3. Log to S3 (Your original logic, preserved)
    try:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_features": input_data,
            "prediction_label": label,
            "prediction_probability": proba,
            "model_version": model_state["version"],  # Added version for debugging
        }

        current_date = datetime.now(timezone.utc)
        object_key = (
            f"year={current_date.year}/"
            f"month={current_date.month:02d}/"
            f"day={current_date.day:02d}/"
            f"{current_date.isoformat()}.json"
        )

        s3_client.put_object(
            Bucket=LOG_BUCKET_NAME,
            Key=object_key,
            Body=json.dumps(log_data),
        )
    except Exception as e:
        # We log the error but don't fail the request (Best Practice)
        logger.error(f"S3 Logging failed: {e}")

    return {"failure_risk": proba, "label": label, "version": model_state["version"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
