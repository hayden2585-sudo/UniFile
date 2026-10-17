FROM python:3.11-slim

LABEL maintainer="Soniscorett Labs <labs@soniscorett.ai>"
LABEL description="Unifile by Soniscorett - Universal Read-Only File Translator Connector for AI Models"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY pyproject.toml setup.py /app/
RUN pip install --no-cache-dir .

# Copy application code and assets
COPY unifile /app/unifile
COPY static /app/static
COPY samples /app/samples

EXPOSE 8000

# Default command: launch Unifile server
CMD ["python3", "-m", "unifile.cli", "--server", "--port", "8000", "--host", "0.0.0.0"]
