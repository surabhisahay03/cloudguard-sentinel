import os

import joblib
import mlflow
import mlflow.xgboost
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# --- CONFIGURATION ---
# 1. We read the MLflow URL from the environment (injected by K8s)
#    Defaulting to the internal DNS we found earlier.
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:80")
EXPERIMENT_NAME = "machine-failure-prediction-v2"


def train():
    # 2. Connect to the MLflow Server
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    print(f"1. Connecting to Tracking URI: {MLFLOW_TRACKING_URI}")

    # --- ENHANCED DEBUGGING ---
    # Set the experiment
    experiment = mlflow.set_experiment(EXPERIMENT_NAME)

    # Print what the server told us!
    print(f"2. Experiment Name: {experiment.name}")
    print(f"3. Experiment ID:   {experiment.experiment_id}")
    print(f"4. Artifact Loc:    {experiment.artifact_location}")
    print(f"5. Lifecycle Stage: {experiment.lifecycle_stage}")
    # ^^^ If this says 'deleted', that's your smoking gun!

    print(f"Starting MLflow run on {MLFLOW_TRACKING_URI}...")

    # 3. Load Data (Same as before)
    print("Loading data...")
    # In a real scenario, you might download from S3 here.
    # For now, we use the local CSV baked into the Docker image.
    df = pd.read_csv("ai4i2020.csv")

    # 4. Feature Engineering (Identical to your old code)
    print("Performing feature engineering...")
    df = df.rename(
        columns={
            "Air temperature [K]": "air_temp_k",
            "Process temperature [K]": "proc_temp_k",
            "Rotational speed [rpm]": "rpm",
            "Torque [Nm]": "torque_nm",
            "Tool wear [min]": "tool_wear_min",
            "Machine failure": "failure",
        }
    )

    df["temp_diff_k"] = df["proc_temp_k"] - df["air_temp_k"]
    df["power"] = df["torque_nm"] * df["rpm"]
    df = pd.get_dummies(df, columns=["Type"], prefix="type")

    # Ensure all expected columns exist (handling missing categories)
    for col in ["type_L", "type_M", "type_H"]:
        if col not in df.columns:
            df[col] = False

    features = [
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
    target = "failure"

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5. The Magic Block: Everything inside here is tracked
    with mlflow.start_run():

        # Define Hyperparameters
        n_estimators = 100
        max_depth = 6
        learning_rate = 0.1

        # A. Log Parameters (So we remember them later)
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_param("learning_rate", learning_rate)

        # B. Train Model
        print("Training model...")
        model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            use_label_encoder=False,
            eval_metric="logloss",
        )
        model.fit(X_train, y_train)

        # C. Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Accuracy: {accuracy}")

        # D. Log Metrics (So we can see the graph)
        mlflow.log_metric("accuracy", accuracy)

        # E. Save & Upload Model (Replaces your manual S3 upload)
        # This sends the model to s3://.../mlflow/...
        print("Uploading model to MLflow Artifact Store...")
        mlflow.sklearn.log_model(model, "model")
        print("Model uploaded successfully!")

        # We also save locally just for backward compatibility if needed
        joblib.dump(model, "model_v2.joblib")


if __name__ == "__main__":
    train()
