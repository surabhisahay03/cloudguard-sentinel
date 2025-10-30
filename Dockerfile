# -----------------------
# Stage 1: Builder
# -----------------------
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install dependencies separately for caching
COPY app/requirements.txt .

RUN pip install --upgrade pip \
 && pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# -----------------------
# Stage 2: Runtime
# -----------------------
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# RUN useradd -m appuser
# USER appuser

# Copy wheels and install only necessary packages
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy app source code
COPY app /app

# Expose port
EXPOSE 8000

# Command to run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
#   CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1