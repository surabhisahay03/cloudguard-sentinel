import hashlib
import os

# import joblib
import mlflow
import mlflow.xgboost
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# --- CONFIGURATION ---
# 1. We read the MLflow URL from the environment (injected by K8s)
#    Defaulting to the internal DNS we found earlier.
MODEL_NAME = "machine-failure-prediction"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:80")
EXPERIMENT_NAME = "machine-failure-prediction-v2"


def calculate_data_hash(df):
    """Calculate a simple hash of the dataframe for versioning purposes."""
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values).hexdigest()


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
    # In a real scenario, we might download from S3 here.
    # For now, we use the local CSV baked into the Docker image.
    df = pd.read_csv("ai4i2020.csv")

    data_hash = calculate_data_hash(df)
    print(f"Dataset Hash: {data_hash}")

    # 4. Feature Engineering
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

        # Log the data hash
        mlflow.log_param("dataset_hash", data_hash)

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
        new_accuracy = accuracy_score(y_test, y_pred)
        print(f"Accuracy: {new_accuracy}")

        # D. Log Metrics (So we can see the graph)
        mlflow.log_metric("accuracy", new_accuracy)

        client = mlflow.MlflowClient()
        promote_model = False

        try:
            # Get the current production model
            prod_models = client.get_latest_versions(MODEL_NAME, stages=["production"])

            if prod_models:
                current_prod_version = prod_models[0].version
                current_prod_run_id = prod_models[0].run_id

                # Fetch the accuracy of the current production model
                prod_metric = client.get_metric_history(current_prod_run_id, "accuracy")
                current_accuracy = prod_metric[0].value if prod_metric else 0.0

                print(
                    f"Current Production Model Version: {current_prod_version} with Accuracy: \
                    {current_accuracy}"
                )

                # Compare accuracies
                if new_accuracy >= current_accuracy:
                    print(
                        "New model outperforms or matches the current production model."
                        " Promoting to Production."
                    )
                    promote_model = True
                else:
                    print(
                        "New model does not outperform the current production model. Not promoting."
                    )
            else:
                print(
                    "No production model found. Promoting the new model to Production by default."
                )
                promote_model = True
        except Exception as e:
            print(f"Error checking current production model: {e}")
            print("Promoting the new model to Production by default.")
            promote_model = True

        # Log the model
        mv = mlflow.sklearn.log_model(model, "model")

        # Register and Promote if it passed the test
        if promote_model:
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/model"
            mv = mlflow.register_model(model_uri, MODEL_NAME)

            # Transition to Production
            client.transition_model_version_stage(
                name=MODEL_NAME,
                version=mv.version,
                stage="production",
                archive_existing_versions=True,
            )
        # E. Save & Upload Model (Replaces your manual S3 upload)
        # This sends the model to s3://.../mlflow/...
        print("Uploading model to MLflow Artifact Store...")

        print("Model uploaded successfully!")

        # We also save locally just for backward compatibility if needed
        # joblib.dump(model, "model_v2.joblib")


if __name__ == "__main__":
    train()
