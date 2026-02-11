# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

WORKDIR /app

# System deps (needed to build some Python wheels)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Guardrails hub validators (uses BuildKit secret)
RUN --mount=type=secret,id=guardrails_key \
    printf "n\nn\n" | guardrails configure --token "$(cat /run/secrets/guardrails_key)" && \
    guardrails hub install hub://guardrails/toxic_language && \
    rm -rf ~/.guardrails

# App code
COPY . .

# Cloud Run expects port 8080
ENV PORT=8080

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
