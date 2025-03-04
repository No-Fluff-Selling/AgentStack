FROM python:3.11 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.in-project true
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY . .
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8000

CMD ["uvicorn", "agent_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug", "--no-access-log"]
