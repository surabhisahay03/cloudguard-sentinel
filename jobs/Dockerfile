FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install pandas scikit-learn xgboost boto3 joblib s3fs

# Copy training script
COPY train.py .
COPY ai4i2020.csv .

# Command to run the training script
CMD ["python", "train.py"]
