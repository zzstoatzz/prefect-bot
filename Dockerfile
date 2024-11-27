FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1
ENV PATH="/root/.local/bin:$PATH"

COPY requirements.txt .

RUN uv pip install -r requirements.txt

COPY main.py .
