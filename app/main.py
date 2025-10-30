import os

import psutil
from fastapi import FastAPI

app = FastAPI(title="CloudGuard Sentinel API", version="1.0.0")


@app.get("/health")
def health():
    """Basic health check endpoint"""
    return {"status": "ok", "service": "cloudguard-sentinel"}


@app.get("/predict")
def predict():
    """Dummy inference endpoint"""
    return {"message": "This is a placeholder prediction response"}


@app.get("/metrics")
def metrics():
    """Simple system metrics endpoint"""
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 * 1024)
    cpu = psutil.cpu_percent(interval=0.1)
    return {"cpu_percent": cpu, "memory_mb": round(mem, 2)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
