import os
from io import BytesIO

import boto3
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# Configurations.
BUCKET_NAME = os.getenv("LOG_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_PREFIX", "year=2025")

s3_client = boto3.client("s3")


def load_data_from_s3():
    print(f"Loading data from S3 bucket: {BUCKET_NAME}, with prefix: {S3_PREFIX}")
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=S3_PREFIX)

    data_frames = []
    if "Contents" not in response:
        print("No data found in the specified S3 bucket and prefix.")
        return pd.DataFrame()

    for obj in response["Contents"]:
        key = obj["Key"]
        if key.endswith(".json"):
            print(f"Downloading {key}...")
            obj_body = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)["Body"].read()
            # We assume the JSON is a single record or list of records
            df = pd.read_json(BytesIO(obj_body), lines=True)
            data_frames.append(df)

    if not data_frames:
        print("No JSON files found in the specified S3 bucket and prefix.")
        return pd.DataFrame()

    full_df = pd.concat(data_frames, ignore_index=True)
    return full_df


def train():

    print("Starting training process...")

    # 1. Load Data
    # For this "Phase 1" of training, since we don't have the labels merged yet,
    # we will just load the local CSV to prove the pipeline works.
    # In the real final version, we uncomment load_data_from_s3()
    # df = load_data_from_s3()

    print("NOTE: Simulating S3 fetch by using local base dataset for 'Smoke Test'")
    df = pd.read_csv("ai4i2020.csv")

    # 2. Feature Engineering (The "Magic" Step)
    print("Performing feature engineering...")

    # A. Rename columns to match your model's expected input
    df = df.rename(
        columns={
            "Machine failure": "Target",
            "Rotational speed [rpm]": "rpm",
            "Torque [Nm]": "torque_nm",
            "Tool wear [min]": "tool_wear_min",
            "Air temperature [K]": "air_temp_k",
            "Process temperature [K]": "proc_temp_k",
        }
    )

    # B. Create the new calculated features (from your screenshot)
    df["temp_diff_k"] = df["proc_temp_k"] - df["air_temp_k"]
    df["power"] = df["torque_nm"] * df["rpm"]

    # C. One-Hot Encode the 'Type' column (L, M, H)
    # We create 3 boolean columns manually to ensure they always exist
    df["type_L"] = (df["Type"] == "L").astype(bool)
    df["type_M"] = (df["Type"] == "M").astype(bool)
    df["type_H"] = (df["Type"] == "H").astype(bool)

    # D. Define the exact feature list (Order matters!)
    # This matches the 15 columns from your X_test.shape screenshot
    feature_cols = [
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

    # E. Separate Features (X) and Target (y)
    X = df[feature_cols]
    y = df["Target"]

    print(f"Data Shape: {X.shape}")
    print(f"Features: {X.columns.tolist()}")

    # 3. Train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = XGBClassifier()
    model.fit(X_train, y_train)

    # 4. Evaluate
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Model training Complete. Accuracy: {acc:.4f}")

    # 5. Save Model (to be updated later)
    joblib.dump(model, "model_v2.joblib")
    print("Model saved to model_v2.joblib")

    # 6. Upload model to S3 for deployment
    s3_key = "models/model_v2.joblib"
    print(f"Uploading model to S3 bucket: {BUCKET_NAME}, key: {s3_key}")

    s3_client.upload_file("model_v2.joblib", BUCKET_NAME, s3_key)
    print("Model upload completed to S3!")


if __name__ == "__main__":
    train()
