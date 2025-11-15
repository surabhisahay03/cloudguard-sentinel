# ml/src/train.py
import json
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

# Define the absolute path to the project's root folder
# Use .resolve() to get the absolute path, protecting against symlinks or relative (..) paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROC = PROJECT_ROOT / "data_proc"
OUT_DIR = PROJECT_ROOT / "models"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_splits():
    """
    Load preprocessed train/val/test splits from parquet files.
    :return: X_train, y_train, X_val, y_val, X_test, y_test, feature_list
    """
    X_train = pd.read_parquet(PROC / "X_train.parquet")
    y_train = pd.read_parquet(PROC / "y_train.parquet")["failure"].astype(int)

    X_val = pd.read_parquet(PROC / "X_val.parquet")
    y_val = pd.read_parquet(PROC / "y_val.parquet")["failure"].astype(int)

    X_test = pd.read_parquet(PROC / "X_test.parquet")
    y_test = pd.read_parquet(PROC / "y_test.parquet")["failure"].astype(int)

    feature_list = json.loads((PROC / "feature_list.json").read_text())

    # Ensure all datasets have the *exact same* column order as defined in feature_list
    # This prevents the model from getting confused if files were saved differently.
    X_train = X_train[feature_list]
    X_val = X_val[feature_list]
    X_test = X_test[feature_list]
    return X_train, y_train, X_val, y_val, X_test, y_test, feature_list


def evaluate(clf, X, y):
    """
    Evaluate classifier and return key metrics.
    :param clf: trained classifier
    :param X: features
    :param y: true labels
    :return: dict of metrics
    """
    proba = clf.predict_proba(X)[:, 1]
    preds = (proba >= 0.5).astype(int)

    # AUC-ROC: Area Under the Receiver Operating Characteristic Curve.
    # AUC-PR: Area Under the Precision-Recall Curve.
    return {
        "auc_roc": float(roc_auc_score(y, proba)),
        "auc_pr": float(average_precision_score(y, proba)),
        "f1": float(f1_score(y, preds, zero_division=0)),
        "precision": float(precision_score(y, preds, zero_division=0)),
        "recall": float(recall_score(y, preds, zero_division=0)),
    }


def main():
    # Local MLflow tracking — stores runs in ./mlruns/ by default
    mlflow.set_experiment("cloudguard_ai4i")

    X_train, y_train, X_val, y_val, X_test, y_test, feature_list = load_splits()

    # Handle class imbalance (scale_pos_weight = neg/pos)
    pos = max(1, int(y_train.sum()))
    neg = int((y_train == 0).sum())
    spw = neg / pos

    params = {
        "n_estimators": 300,
        "max_depth": 5,
        "learning_rate": 0.08,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
        "eval_metric": "logloss",
        "scale_pos_weight": spw,  # imbalance fix
        "use_label_encoder": False,
    }

    with mlflow.start_run():
        mlflow.log_params(params)
        mlflow.log_param("scale_pos_weight", spw)

        clf = XGBClassifier(**params)
        clf.fit(X_train, y_train)

        # Evaluate on val & test
        m_val = evaluate(clf, X_val, y_val)
        m_tst = evaluate(clf, X_test, y_test)

        mlflow.log_metrics({f"val_{k}": v for k, v in m_val.items()})
        mlflow.log_metrics({f"test_{k}": v for k, v in m_tst.items()})

        # Persist artifacts: model, feature list, metrics
        model_path = OUT_DIR / "model_xgb.pkl"
        joblib.dump(clf, model_path)
        (OUT_DIR / "feature_list.json").write_text(json.dumps(feature_list))

        mlflow.log_artifact(str(model_path))
        mlflow.log_artifact(str(OUT_DIR / "feature_list.json"))

        # Also log a MLflow "flavored" model (optional)
        mlflow.sklearn.log_model(clf, artifact_path="model")

        print("✅ Trained. Val metrics:", m_val)
        print("✅ Test  metrics:", m_tst)
        print(f"✅ Saved: {model_path} and feature_list.json in {OUT_DIR}")


if __name__ == "__main__":
    main()
