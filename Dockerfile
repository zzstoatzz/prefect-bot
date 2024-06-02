FROM prefecthq/prefect:3.0.0rc1-python3.12

WORKDIR /app

RUN pip install uv
RUN uv venv

COPY requirements.txt .

RUN uv pip install -r requirements.txt