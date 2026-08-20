FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./src /app/src
COPY ./config /app/config
COPY ./alembic.ini /app/alembic.ini
COPY ./pyproject.toml /app/pyproject.toml

# Create non-root user
RUN groupadd -r sentinel && useradd -r -g sentinel sentinel
RUN chown -R sentinel:sentinel /app
USER sentinel

# Expose API port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
